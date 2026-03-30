import argparse
import concurrent.futures
import json
import os
import re
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
from urllib import request as urllib_request
from urllib import error as urllib_error

from sqlalchemy import create_engine, text


SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://dbjkwhwqulvzvddxpbmj.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
EVIDENCE_BUCKET = str(os.getenv("EVIDENCE_BUCKET") or "evidence-frame").strip()
EXAM_LOGS_BUCKET = "exam-logs"
EVIDENCE_MAX_ITEMS = int(os.getenv("EVIDENCE_MAX_ITEMS", "300"))
EVIDENCE_SIGNED_URL_EXPIRES_IN = int(os.getenv("EVIDENCE_SIGNED_URL_EXPIRES_IN", "31536000"))
SUPABASE_SIGNED_URL_EXPIRES_IN = int(os.getenv("SUPABASE_SIGNED_URL_EXPIRES_IN", "604800"))


def _write_evidence_manifest_file(report_output_path: Path, evidence_frames: dict[str, Any]) -> str:
	"""Write a standalone evidence manifest JSON beside the report JSON file."""
	manifest_items: list[dict[str, Any]] = []
	for item in list(evidence_frames.get("items") or []):
		manifest_items.append(
			{
				"url": item.get("evidence_frame"),
				"file_name": item.get("file_name"),
				"time": item.get("time"),
				"bucket": item.get("bucket"),
				"supabase_path": item.get("supabase_path"),
				"warning_folder": item.get("warning_folder"),
				"sectionid": item.get("sectionid"),
				"testid": item.get("testid"),
			}
		)

	manifest = {
		"generated_at": datetime.utcnow().isoformat() + "Z",
		"signed_url_expires_in": EVIDENCE_SIGNED_URL_EXPIRES_IN,
		"total": len(manifest_items),
		"page_size": 10,
		"items": manifest_items,
	}

	manifest_path = report_output_path.with_name(f"{report_output_path.stem}_evidence_frames.json")
	manifest_path.write_text(
		json.dumps(manifest, indent=2, ensure_ascii=False, default=_json_default),
		encoding="utf-8",
	)
	return str(manifest_path)


def _load_env_file(env_path: Path) -> None:
	if not env_path.exists():
		return

	for raw_line in env_path.read_text(encoding="utf-8").splitlines():
		line = raw_line.strip()
		if not line or line.startswith("#") or "=" not in line:
			continue
		key, value = line.split("=", 1)
		key = key.strip()
		value = value.strip().strip('"').strip("'")
		# Treat empty process env vars as unset so .env can provide defaults.
		if key and not str(os.environ.get(key) or "").strip():
			os.environ[key] = value


def _json_parse(value: Any) -> Any:
	if value is None:
		return None
	if isinstance(value, (dict, list)):
		return value
	if isinstance(value, (bytes, bytearray)):
		value = value.decode("utf-8", errors="replace")
	if isinstance(value, str):
		stripped = value.strip()
		if not stripped:
			return None
		try:
			return json.loads(stripped)
		except json.JSONDecodeError:
			return value
	return value


def _json_default(value: Any) -> str:
	if hasattr(value, "isoformat"):
		return value.isoformat()
	return str(value)


def _supabase_headers() -> dict[str, str]:
	key = str(os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or SUPABASE_SERVICE_ROLE_KEY or "").strip()
	return {
		"apikey": key,
		"Authorization": f"Bearer {key}",
		"Content-Type": "application/json",
	}


def _supabase_list_prefix(bucket: str, prefix: str) -> list[dict[str, Any]]:
	supabase_url = str(os.getenv("SUPABASE_URL") or SUPABASE_URL or "").strip().rstrip("/")
	if not supabase_url:
		return []
	headers = _supabase_headers()
	if not headers.get("apikey"):
		return []

	list_url = f"{supabase_url}/storage/v1/object/list/{bucket}"
	payload = {
		"prefix": prefix,
		"limit": 1000,
		"offset": 0,
		"sortBy": {"column": "name", "order": "asc"},
	}
	req = urllib_request.Request(
		url=list_url,
		data=json.dumps(payload).encode("utf-8"),
		headers=headers,
		method="POST",
	)
	try:
		with urllib_request.urlopen(req, timeout=8) as resp:
			raw = resp.read().decode("utf-8")
			parsed = json.loads(raw or "[]")
			return parsed if isinstance(parsed, list) else []
	except (urllib_error.URLError, urllib_error.HTTPError, TimeoutError, json.JSONDecodeError):
		return []


def _supabase_list_files_recursive(bucket: str, base_prefix: str, max_depth: int = 8) -> list[str]:
	# Supabase list API is prefix-based and typically returns one-level names.
	# Walk recursively to collect concrete file object paths.
	queue: list[tuple[str, int]] = [(base_prefix, 0)]
	visited: set[str] = set()
	files: list[str] = []
	file_exts = {
		"jpg", "jpeg", "png", "webp", "gif", "bmp", "json", "txt", "log", "csv", "pdf", "zip"
	}

	while queue:
		prefix, depth = queue.pop(0)
		if prefix in visited or depth > max_depth:
			continue
		visited.add(prefix)

		entries = _supabase_list_prefix(bucket=bucket, prefix=prefix)
		for entry in entries:
			name = str(entry.get("name") or "").strip()
			if not name:
				continue

			full = f"{prefix}/{name}" if not name.startswith(f"{prefix}/") else name
			if full.endswith("/"):
				full = full.rstrip("/")

			base_name = full.split("/")[-1]
			ext = base_name.rsplit(".", 1)[-1].lower() if "." in base_name else ""

			# Folder names can legitimately contain dots (for example warning text with decimals).
			# Treat as file only when extension is a known file type; otherwise continue traversal.
			if ext and ext in file_exts:
				files.append(full)
			else:
				queue.append((full, depth + 1))

	# Deduplicate while preserving deterministic ordering.
	return sorted(set(files))


def _supabase_signed_url(bucket: str, object_path: str, expires_in: int | None = None) -> str | None:
	supabase_url = str(os.getenv("SUPABASE_URL") or SUPABASE_URL or "").strip().rstrip("/")
	if not supabase_url:
		return None
	headers = _supabase_headers()
	if not headers.get("apikey"):
		return None
	if expires_in is None:
		expires_in = SUPABASE_SIGNED_URL_EXPIRES_IN

	sign_url = f"{supabase_url}/storage/v1/object/sign/{bucket}/{object_path}"
	req = urllib_request.Request(
		url=sign_url,
		data=json.dumps({"expiresIn": int(expires_in)}).encode("utf-8"),
		headers=headers,
		method="POST",
	)
	try:
		with urllib_request.urlopen(req, timeout=8) as resp:
			raw = resp.read().decode("utf-8")
			payload = json.loads(raw or "{}")
			signed = payload.get("signedURL") or payload.get("signedUrl")
			if not signed:
				return None
			signed = str(signed)
			if signed.startswith("http"):
				return signed.replace(".supabase.co/object/sign/", ".supabase.co/storage/v1/object/sign/")
			if signed.startswith("/storage/v1/"):
				return f"{supabase_url}{signed}"
			if signed.startswith("/object/"):
				return f"{supabase_url}/storage/v1{signed}"
			return f"{supabase_url}/storage/v1/{signed.lstrip('/')}"
	except (urllib_error.URLError, urllib_error.HTTPError, TimeoutError, json.JSONDecodeError, Exception):
		return None


def _attach_signed_links(
	bucket: str,
	items: list[dict[str, Any]],
	path_key: str,
	url_key: str,
	expires_in: int | None = None,
) -> None:
	paths = [str(item.get(path_key) or "").strip() for item in items]
	paths = [p for p in paths if p]
	if not paths:
		return

	unique_paths = list(dict.fromkeys(paths))
	path_to_url: dict[str, str | None] = {}

	def _sign(path: str) -> tuple[str, str | None]:
		return path, _supabase_signed_url(bucket, path, expires_in=expires_in)

	with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
		for path, url in executor.map(_sign, unique_paths):
			path_to_url[path] = url

	for item in items:
		path = str(item.get(path_key) or "").strip()
		item[url_key] = path_to_url.get(path)


def _safe_email_segment(email: str) -> str:
	return str(email or "unknown").strip().lower().replace("@", "_at_").replace("/", "_").replace("\\", "_")


def _to_iso_from_epoch_fragment(value: str) -> str | None:
	try:
		epoch = float(value)
		return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
	except (TypeError, ValueError, OSError):
		return None


def _to_epoch_seconds(value: Any) -> float | None:
	if value is None:
		return None
	try:
		if isinstance(value, datetime):
			dt = value
		else:
			raw = str(value).strip().replace("Z", "+00:00")
			dt = datetime.fromisoformat(raw)
		if dt.tzinfo is None:
			dt = dt.replace(tzinfo=timezone.utc)
		return dt.timestamp()
	except (TypeError, ValueError):
		return None


def _collect_supabase_evidence(
	email: str,
	selected_attempt_id: int | None = None,
	drive_id: int | None = None,
	identifier_candidates: list[Any] | None = None,
	start_time: Any = None,
	end_time: Any = None,
) -> dict[str, Any]:
	primary_bucket = str(EVIDENCE_BUCKET or "").strip()
	bucket_candidates = [b for b in [primary_bucket, "evidence-frames", "evidence-frame"] if b]
	bucket_candidates = list(dict.fromkeys(bucket_candidates))

	base_prefix = _safe_email_segment(email)
	selected_attempt_id_int = _to_int(selected_attempt_id, default=0)
	allowed_testids: set[str] = set()
	if selected_attempt_id_int > 0:
		allowed_testids.add(str(selected_attempt_id_int))
	if _to_int(drive_id, default=0) > 0:
		allowed_testids.add(str(_to_int(drive_id, default=0)))
	for candidate in list(identifier_candidates or []):
		candidate_int = _to_int(candidate, default=0)
		if candidate_int > 0:
			allowed_testids.add(str(candidate_int))
	start_epoch = _to_epoch_seconds(start_time)
	end_epoch = _to_epoch_seconds(end_time)
	if start_epoch is not None and end_epoch is not None and start_epoch > end_epoch:
		start_epoch, end_epoch = end_epoch, start_epoch
	window_slack_sec = 300
	items: list[dict[str, Any]] = []
	bucket_hits: dict[str, int] = {}

	for bucket in bucket_candidates:
		objects = _supabase_list_files_recursive(bucket=bucket, base_prefix=base_prefix)
		if not objects:
			continue

		for full_path in objects:
			if not full_path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
				continue

			parts = full_path.split("/")
			# expected: email_safe/testid/sectionid/warning_dir/file.jpg
			if len(parts) < 5:
				continue

			testid = parts[1]
			sectionid = parts[2]
			warning_dir = parts[3]
			file_name = parts[-1]

			match = re.search(r"_(\d{9,13})\.jpg$", file_name)
			frame_epoch = None
			if match:
				try:
					frame_epoch = float(match.group(1))
				except (TypeError, ValueError):
					frame_epoch = None
			time_iso = _to_iso_from_epoch_fragment(match.group(1)) if match else None

			# Keep only artifacts belonging to selected attempt context.
			matches_testid = bool(allowed_testids) and str(testid) in allowed_testids
			matches_time_window = (
				start_epoch is not None
				and end_epoch is not None
				and frame_epoch is not None
				and (start_epoch - window_slack_sec) <= frame_epoch <= (end_epoch + window_slack_sec)
			)
			if allowed_testids or (start_epoch is not None and end_epoch is not None):
				if not (matches_testid or matches_time_window):
					continue

			items.append(
				{
					"bucket": bucket,
					"testid": testid,
					"sectionid": sectionid,
					"warning_folder": warning_dir,
					"file_name": file_name,
					"time": time_iso,
					"supabase_path": full_path,
					"evidence_frame": None,
				}
			)

	total_matched_items = len(items)
	truncated_count = 0
	if EVIDENCE_MAX_ITEMS > 0 and total_matched_items > EVIDENCE_MAX_ITEMS:
		items.sort(
			key=lambda x: (
				str(x.get("time") or ""),
				str(x.get("warning_folder") or ""),
				str(x.get("file_name") or ""),
			),
			reverse=True,
		)
		items = items[:EVIDENCE_MAX_ITEMS]
		truncated_count = total_matched_items - len(items)

	for bucket in bucket_candidates:
		bucket_items = [item for item in items if str(item.get("bucket")) == bucket]
		_attach_signed_links(
			bucket=bucket,
			items=bucket_items,
			path_key="supabase_path",
			url_key="evidence_frame",
			expires_in=EVIDENCE_SIGNED_URL_EXPIRES_IN,
		)
		bucket_hits[bucket] = sum(1 for item in bucket_items if item.get("evidence_frame"))

	items.sort(key=lambda x: (str(x.get("testid") or ""), str(x.get("sectionid") or ""), str(x.get("time") or ""), str(x.get("file_name") or "")))
	return {
		"bucket": primary_bucket,
		"searched_buckets": bucket_candidates,
		"selected_attempt_id": _to_int(selected_attempt_id, default=0),
		"selected_drive_id": _to_int(drive_id, default=0),
		"allowed_testids": sorted(list(allowed_testids)),
		"bucket_hits": bucket_hits,
		"base_prefix": base_prefix,
		"count": len(items),
		"total_matched_items": total_matched_items,
		"truncated_count": truncated_count,
		"items": items,
	}


def _collect_supabase_logs(email: str, selected_attempt_id: int | None) -> dict[str, Any]:
	bucket = str(EXAM_LOGS_BUCKET or "").strip()
	if not bucket:
		return {"bucket": None, "base_prefix": None, "items": [], "latest": None}

	base_prefix = _safe_email_segment(email)
	items: list[dict[str, Any]] = []
	attempt_id = _to_int(selected_attempt_id, default=0)
	if attempt_id <= 0:
		return {
			"bucket": bucket,
			"base_prefix": base_prefix,
			"selected_attempt_id": 0,
			"count": 0,
			"latest": None,
			"latest_exam_log": None,
			"items": [],
		}

	prefix = f"{base_prefix}/{attempt_id}"
	objects = _supabase_list_files_recursive(bucket=bucket, base_prefix=prefix)
	for full_path in objects:

		items.append(
			{
				"attempt_id": attempt_id,
				"file_name": full_path.split("/")[-1],
				"supabase_path": full_path,
				"logs_link": None,
			}
		)

	_attach_signed_links(bucket=bucket, items=items, path_key="supabase_path", url_key="logs_link")

	latest = items[-1] if items else None
	latest_exam_log = None
	for row in reversed(items):
		if str(row.get("file_name") or "").lower() == "exam.log":
			latest_exam_log = row
			break
	return {
		"bucket": bucket,
		"base_prefix": base_prefix,
		"selected_attempt_id": attempt_id,
		"count": len(items),
		"latest": latest,
		"latest_exam_log": latest_exam_log,
		"items": items,
	}


def _resolve_candidate_and_launch(conn, email: str, launch_code: str) -> dict[str, Any]:
	row = conn.execute(
		text(
			"""
			SELECT
				u.user_id,
				u.email,
				u.role,
				u.is_active,
				u.email_verified,
				u.created_at AS user_created_at,
				c.candidate_id,
				c.full_name,
				c.mobile_no,
				c.country,
				c.timezone,
				c.photo_url,
				c.years_of_experience,
				c.onboarding_step,
				c.created_at AS candidate_created_at,
				elc.launch_id,
				elc.registration_id,
				elc.drive_id,
				elc.launch_code,
				elc.expires_at,
				elc.used_at,
				elc.created_at AS launch_created_at
			FROM users u
			JOIN candidates c ON c.user_id = u.user_id
			JOIN exam_launch_codes elc ON elc.candidate_id = c.candidate_id
			WHERE LOWER(u.email) = LOWER(:email)
			  AND UPPER(elc.launch_code) = UPPER(:launch_code)
			ORDER BY elc.launch_id DESC
			LIMIT 1
			"""
		),
		{"email": email, "launch_code": launch_code},
	).mappings().first()

	if not row:
		raise ValueError("No record found for this email + launch code pair.")

	return dict(row)


def _resolve_exam(conn, drive_id: int) -> dict[str, Any]:
	row = conn.execute(
		text(
			"""
			SELECT
				d.drive_id,
				d.title,
				d.description,
				d.eligibility,
				d.start_date,
				d.end_date,
				d.exam_date,
				d.duration_minutes,
				d.max_attempts,
				d.exam_type,
				d.generation_mode,
				d.is_published,
				d.key_topics,
				d.specializations,
				d.max_marks,
				d.status,
				d.created_at,
				v.vendor_id,
				v.company_name,
				v.organization_type,
				v.organization_email
			FROM drives d
			LEFT JOIN vendors v ON v.vendor_id = d.vendor_id
			WHERE d.drive_id = :drive_id
			"""
		),
		{"drive_id": drive_id},
	).mappings().first()

	if not row:
		raise ValueError(f"Exam {drive_id} was not found.")

	exam = dict(row)
	exam["key_topics"] = _json_parse(exam.get("key_topics")) or []
	exam["specializations"] = _json_parse(exam.get("specializations")) or []
	return exam


def _resolve_attempt(conn, candidate_id: int, drive_id: int) -> dict[str, Any]:
	rows = conn.execute(
		text(
			"""
			SELECT
				ea.attempt_id,
				ea.drive_id,
				ea.candidate_id,
				ea.start_time,
				ea.end_time,
				ea.total_marks,
				ea.status,
				ea.created_at,
				EXISTS(SELECT 1 FROM answers a WHERE a.attempt_id = ea.attempt_id) AS has_answers,
				EXISTS(SELECT 1 FROM jit_answer_events jae WHERE jae.attempt_id = ea.attempt_id) AS has_jit,
				EXISTS(SELECT 1 FROM code_submissions cs WHERE cs.attempt_id = ea.attempt_id) AS has_coding
			FROM exam_attempts ea
			WHERE ea.candidate_id = :candidate_id
			  AND ea.drive_id = :drive_id
			ORDER BY ea.created_at DESC, ea.attempt_id DESC
			"""
		),
		{"candidate_id": candidate_id, "drive_id": drive_id},
	).mappings().all()

	if not rows:
		return {"selected_attempt": None, "all_attempts": []}

	all_attempts = [dict(r) for r in rows]
	# Always choose the latest attempt snapshot for report selection.
	selected_attempt = all_attempts[0]

	return {
		"selected_attempt": selected_attempt,
		"all_attempts": all_attempts,
	}


def _fetch_sections(conn, drive_id: int) -> list[dict[str, Any]]:
	rows = conn.execute(
		text(
			"""
			SELECT
				section_id,
				drive_id,
				title,
				section_type,
				question_type,
				order_index,
				planned_question_count,
				marks_weight,
				status,
				created_at
			FROM exam_sections
			WHERE drive_id = :drive_id
			ORDER BY order_index ASC, section_id ASC
			"""
		),
		{"drive_id": drive_id},
	).mappings().all()
	return [dict(r) for r in rows]


def _fetch_static_questions_with_answers(conn, attempt_id: int, drive_id: int) -> list[dict[str, Any]]:
	rows = conn.execute(
		text(
			"""
			SELECT
				q.question_id,
				q.section_id,
				q.question_type,
				q.question_text,
				q.payload_json,
				q.option_a,
				q.option_b,
				q.option_c,
				q.option_d,
				q.correct_option,
				q.marks,
				q.taxonomy_level,
				q.morphing_strategy,
				q.time_complexity,
				q.space_complexity,
				a.answer_id,
				a.selected_option,
				a.marks_obtained
			FROM questions q
			LEFT JOIN answers a
			  ON a.question_id = q.question_id
			 AND a.attempt_id = :attempt_id
			WHERE q.drive_id = :drive_id
			ORDER BY q.section_id ASC, q.question_id ASC
			"""
		),
		{"attempt_id": attempt_id, "drive_id": drive_id},
	).mappings().all()

	result = []
	for row in rows:
		row = dict(row)
		payload = _json_parse(row.get("payload_json"))
		if not isinstance(payload, dict):
			payload = {}
		result.append(
			{
				"section_id": row["section_id"],
				"question_id": row["question_id"],
				"question_type": row["question_type"],
				"question_text": row["question_text"],
				"payload": payload,
				"options": [
					opt
					for opt in [row.get("option_a"), row.get("option_b"), row.get("option_c"), row.get("option_d")]
					if opt is not None and str(opt).strip()
				],
				"correct_answer": payload.get("correct_answer", row.get("correct_option")),
				"candidate_answer": _json_parse(row.get("selected_option")),
				"candidate_answer_raw": row.get("selected_option"),
				"score": row.get("marks_obtained"),
				"max_score": row.get("marks"),
				"taxonomy_level": row.get("taxonomy_level"),
				"morphing_strategy": row.get("morphing_strategy"),
				"time_complexity": row.get("time_complexity"),
				"space_complexity": row.get("space_complexity"),
			}
		)
	return result


def _fetch_jit_events(conn, attempt_id: int) -> list[dict[str, Any]]:
	rows = conn.execute(
		text(
			"""
			SELECT
				jss.section_id,
				jss.section_title,
				jss.question_type AS section_question_type,
				jss.jit_section_session_id,
				jss.jit_session_id,
				jss.planned_question_count,
				jss.asked_count,
				jss.status AS section_status,
				jae.jit_answer_event_id,
				jae.question_id,
				jae.question_number,
				jae.question_payload,
				jae.submitted_answer,
				jae.time_taken_seconds,
				jae.confidence,
				jae.evaluation,
				jae.adaptive_decision,
				jae.score,
				jae.is_correct,
				jae.created_at
			FROM jit_section_sessions jss
			LEFT JOIN jit_answer_events jae
			  ON jae.jit_section_session_id = jss.jit_section_session_id
			 AND jae.attempt_id = jss.attempt_id
			WHERE jss.attempt_id = :attempt_id
			ORDER BY jss.section_id ASC, COALESCE(jae.question_number, 0) ASC, COALESCE(jae.jit_answer_event_id, 0) ASC
			"""
		),
		{"attempt_id": attempt_id},
	).mappings().all()

	result = []
	for row in rows:
		row = dict(row)
		payload = _json_parse(row.get("question_payload"))
		if not isinstance(payload, dict):
			payload = {}
		evaluation = _json_parse(row.get("evaluation"))
		if not isinstance(evaluation, dict):
			evaluation = {}

		raw_score = row.get("score")
		eval_score = evaluation.get("score")
		normalized_score: float = 0.0
		if eval_score is not None:
			try:
				normalized_score = float(eval_score)
			except (TypeError, ValueError):
				normalized_score = 0.0
		else:
			try:
				normalized_score = float(raw_score)
			except (TypeError, ValueError):
				normalized_score = 0.0

		# Legacy rows may store 0..100; normalize to 0..1 for JIT question marks.
		if normalized_score > 1.0:
			normalized_score = normalized_score / 100.0
		normalized_score = max(0.0, min(1.0, normalized_score))

		status_value = str(evaluation.get("status") or "").strip().lower()
		if status_value in {"correct", "partial"}:
			question_result = "pass"
		elif status_value in {"wrong", "incorrect", "timeout", "skipped"}:
			question_result = "fail"
		else:
			question_result = "pass" if normalized_score > 0 else "fail"
		result.append(
			{
				"section_id": row["section_id"],
				"section_title": row["section_title"],
				"question_id": row.get("question_id"),
				"question_number": row.get("question_number"),
				"question_type": payload.get("qtype", row.get("section_question_type")),
				"question_text": payload.get("question_text"),
				"question_payload": payload,
				"candidate_answer": row.get("submitted_answer"),
				"time_taken_seconds": row.get("time_taken_seconds"),
				"confidence": row.get("confidence"),
				"evaluation": evaluation,
				"adaptive_decision": _json_parse(row.get("adaptive_decision")),
				"score": normalized_score,
				"result": question_result,
				"is_correct": row.get("is_correct"),
				"created_at": row.get("created_at"),
			}
		)
	return result


def _fetch_jit_final_reports(conn, attempt_id: int) -> dict[int, dict]:
	"""Fetch topic-strength data for completed JIT section sessions.

	For completed sections where final_report is missing, return a dummy
	"not_applicable" payload so report consumers always receive a stable shape.
	"""
	def _extract_skill_level(report_payload: dict[str, Any]) -> str:
		if not isinstance(report_payload, dict):
			return "not_applicable"

		candidates = [
			report_payload.get("skill_level"),
			report_payload.get("skill"),
			report_payload.get("skill_label"),
			report_payload.get("overall_skill_level"),
		]

		summary = report_payload.get("summary")
		if isinstance(summary, dict):
			candidates.extend(
				[
					summary.get("skill_level"),
					summary.get("skill"),
					summary.get("skill_label"),
					summary.get("overall_skill_level"),
				]
			)

		session_summary = report_payload.get("session_summary")
		if isinstance(session_summary, dict):
			candidates.extend(
				[
					session_summary.get("skill_level"),
					session_summary.get("skill"),
					session_summary.get("skill_label"),
					session_summary.get("overall_skill_level"),
				]
			)

		for item in candidates:
			text = str(item or "").strip()
			if text:
				return text
		return "not_applicable"

	def _theta_to_skill_level(theta_value: Any) -> str:
		try:
			theta = float(theta_value)
		except (TypeError, ValueError):
			return "not_applicable"

		# Matches observed JIT generator labeling where ~2.72 maps to Intermediate.
		if theta < 2.2:
			return "Beginner"
		if theta < 3.0:
			return "Intermediate"
		return "Advanced"

	rows = conn.execute(
		text(
			"""
			SELECT
				jit_section_session_id,
				section_id,
				section_title,
				status,
				final_report
			FROM jit_section_sessions
			WHERE attempt_id = :attempt_id
			"""
		),
		{"attempt_id": attempt_id}
	).mappings().all()

	theta_rows = conn.execute(
		text(
			"""
			SELECT
				t.section_id,
				t.adaptive_decision
			FROM (
				SELECT
					jss.section_id,
					jae.adaptive_decision,
					ROW_NUMBER() OVER (
						PARTITION BY jss.section_id
						ORDER BY COALESCE(jae.question_number, 0) DESC,
						         COALESCE(jae.jit_answer_event_id, 0) DESC
					) AS rn
				FROM jit_section_sessions jss
				JOIN jit_answer_events jae
				  ON jae.jit_section_session_id = jss.jit_section_session_id
				 AND jae.attempt_id = jss.attempt_id
				WHERE jss.attempt_id = :attempt_id
			) t
			WHERE t.rn = 1
			"""
		),
		{"attempt_id": attempt_id},
	).mappings().all()

	latest_theta_by_section: dict[int, float] = {}
	for theta_row in theta_rows:
		section_id = _to_int(theta_row.get("section_id"), default=0)
		if section_id <= 0:
			continue
		adaptive = _json_parse(theta_row.get("adaptive_decision"))
		if isinstance(adaptive, dict):
			new_theta = adaptive.get("new_theta")
			try:
				latest_theta_by_section[section_id] = float(new_theta)
			except (TypeError, ValueError):
				continue

	result = {}
	for row in rows:
		row = dict(row)
		if str(row.get("status") or "").lower() != "completed":
			continue

		skill_level = "not_applicable"
		topic_strength = {
			"sub_topic_mastery": {},
			"sub_topic_attempts": {},
			"strengths": ["not_applicable"],
			"weaknesses": ["not_applicable"],
			"recommendations": ["not_applicable"],
			"skill_level": skill_level,
		}

		if row.get("final_report"):
			try:
				parsed = _json_parse(row.get("final_report"))
				if isinstance(parsed, dict):
					skill_level = _extract_skill_level(parsed)
					topic_strength = {
						"sub_topic_mastery": parsed.get("sub_topic_mastery") or {},
						"sub_topic_attempts": parsed.get("sub_topic_attempts") or {},
						"strengths": parsed.get("strengths") or ["not_applicable"],
						"weaknesses": parsed.get("weaknesses") or ["not_applicable"],
						"recommendations": parsed.get("recommendations") or ["not_applicable"],
						"skill_level": skill_level,
					}
			except Exception:
				pass

		if skill_level == "not_applicable":
			theta_value = latest_theta_by_section.get(_to_int(row.get("section_id"), default=0))
			derived_skill = _theta_to_skill_level(theta_value)
			if derived_skill != "not_applicable":
				skill_level = derived_skill
				topic_strength["skill_level"] = derived_skill

		result[row["section_id"]] = {
			"section_id": row["section_id"],
			"section_title": row["section_title"],
			"section_status": row.get("status"),
			"topic_strength": topic_strength,
			"final_report": _json_parse(row.get("final_report")) if row.get("final_report") else None,
		}

	return result


def _fetch_llm_variants(conn, candidate_id: int, drive_id: int, attempt_id: int) -> list[dict[str, Any]]:
	rows = conn.execute(
		text(
			"""
			SELECT
				lqv.variant_id,
				lqv.section_id,
				lqv.source_question_id,
				lqv.source_question_type,
				lqv.variant_index,
				lqv.morph_type,
				lqv.trace_id,
				lqv.semantic_score,
				lqv.difficulty_actual,
				lqv.selected_for_exam,
				lqv.payload_json,
				lqv.created_at,
				a.selected_option,
				a.marks_obtained,
				q.question_text AS source_question_text,
				q.marks AS source_question_marks,
				q.correct_option AS source_correct_option,
				q.payload_json AS source_payload_json
			FROM llm_question_variants lqv
			LEFT JOIN answers a
			  ON a.question_id = lqv.source_question_id
			 AND a.attempt_id = :attempt_id
			LEFT JOIN questions q
			  ON q.question_id = lqv.source_question_id
			WHERE lqv.candidate_id = :candidate_id
			  AND lqv.exam_id = :drive_id
			  AND lqv.selected_for_exam = true
			ORDER BY lqv.section_id ASC, lqv.source_question_id ASC, lqv.variant_index ASC
			"""
		),
		{
			"candidate_id": candidate_id,
			"drive_id": drive_id,
			"attempt_id": attempt_id,
		},
	).mappings().all()

	result = []
	for row in rows:
		row = dict(row)
		variant_payload = _json_parse(row.get("payload_json"))
		if not isinstance(variant_payload, dict):
			variant_payload = {}
		source_payload = _json_parse(row.get("source_payload_json"))
		if not isinstance(source_payload, dict):
			source_payload = {}

		result.append(
			{
				"section_id": row["section_id"],
				"variant_id": row["variant_id"],
				"source_question_id": row["source_question_id"],
				"source_question_type": row.get("source_question_type"),
				"source_question_text": row.get("source_question_text"),
				"morphed_question_text": variant_payload.get("question_text"),
				"morphed_options": variant_payload.get("options", []),
				"morphed_payload": variant_payload,
				"morph_type": row.get("morph_type"),
				"semantic_score": row.get("semantic_score"),
				"difficulty_actual": row.get("difficulty_actual"),
				"candidate_answer": _json_parse(row.get("selected_option")),
				"candidate_answer_raw": row.get("selected_option"),
				"score": row.get("marks_obtained"),
				"max_score": row.get("source_question_marks"),
				"variant_index": row.get("variant_index"),
				"trace_id": row.get("trace_id"),
				"created_at": row.get("created_at"),
				"source_payload": source_payload,
				"source_correct_answer": source_payload.get("correct_answer", row.get("source_correct_option")),
			}
		)
	return result


def _to_int(value: Any, default: int = 0) -> int:
	try:
		if value is None:
			return default
		return int(float(value))
	except (TypeError, ValueError):
		return default


def _normalize_text(value: Any) -> str:
	return str(value or "").strip().lower()


def _normalize_qtype(value: Any) -> str:
	qtype = _normalize_text(value)
	aliases = {
		"multiple choice": "mcq",
		"multiple_choice": "mcq",
		"multiple select": "msq",
		"multiple_select": "msq",
		"fill in the blanks": "fib",
		"fill_in_the_blank": "fib",
		"fill_blank": "fib",
		"short answer": "short",
		"short_answer": "short",
		"long answer": "long",
		"long_answer": "long",
		"essay": "long",
		"numerical": "numeric",
	}
	return aliases.get(qtype, qtype)


def _normalize_answer_list(value: Any) -> list[str]:
	if isinstance(value, list):
		return [v for v in (_normalize_text(x) for x in value) if v]
	if isinstance(value, str):
		parts = [_normalize_text(x) for x in re.split(r"[,|]", value)]
		cleaned = [x for x in parts if x]
		return cleaned if cleaned else ([_normalize_text(value)] if _normalize_text(value) else [])
	return [_normalize_text(value)] if _normalize_text(value) else []


def _extract_morphed_expected(payload: dict[str, Any], qtype: str) -> Any:
	if qtype == "msq":
		if payload.get("correct_answers") is not None:
			return payload.get("correct_answers")
		if payload.get("correct_answer") is not None:
			return payload.get("correct_answer")

	if qtype in {"mcq", "short", "long", "numeric", "fib"}:
		for key in (
			"correct_answer",
			"correct_answers",
			"answer",
			"answers",
			"correct_option",
			"model_answer",
			"expected_answer",
		):
			if payload.get(key) is not None:
				return payload.get(key)

	return None


def _llm_variant_total_marks(variant: dict[str, Any]) -> int:
	"""Total obtainable marks for one effective morphed question.

	Rules:
	- mcq/msq/short/long/numeric/fib => 1
	- coding => question max marks (fallback 1)
	"""
	payload = variant.get("morphed_payload") if isinstance(variant.get("morphed_payload"), dict) else {}
	qtype = _normalize_qtype(
		payload.get("question_type")
		or payload.get("qtype")
		or variant.get("source_question_type")
	)
	if qtype == "coding":
		return max(1, _to_int(variant.get("max_score"), default=1))
	return 1


def _dedupe_llm_variants_by_source(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
	# Keep a single effective variant per source question using highest variant_id.
	by_source: dict[int, dict[str, Any]] = {}
	for row in rows:
		source_id = _to_int(row.get("source_question_id"), default=0)
		if source_id <= 0:
			continue
		prev = by_source.get(source_id)
		if prev is None:
			by_source[source_id] = row
			continue
		if _to_int(row.get("variant_id")) > _to_int(prev.get("variant_id")):
			by_source[source_id] = row

	return [by_source[sid] for sid in sorted(by_source.keys())]


def _score_llm_variant(variant: dict[str, Any], coding_by_question: dict[int, dict[str, Any]]) -> int:
	# Recompute score from LLM morphed question payload using strict rules.
	payload = variant.get("morphed_payload") if isinstance(variant.get("morphed_payload"), dict) else {}
	qtype = _normalize_qtype(
		payload.get("question_type")
		or payload.get("qtype")
		or variant.get("source_question_type")
	)
	candidate = variant.get("candidate_answer")
	source_payload = variant.get("source_payload") if isinstance(variant.get("source_payload"), dict) else {}
	expected = _extract_morphed_expected(payload, qtype)
	if expected is None:
		expected = _extract_morphed_expected(source_payload, qtype)
	if expected is None:
		expected = variant.get("source_correct_answer")

	max_score = max(1, _to_int(variant.get("max_score"), default=1))

	# Coding: full score only if all test cases pass, otherwise 0.
	if qtype == "coding":
		qid = _to_int(variant.get("source_question_id"), default=0)
		if qid > 0 and qid in coding_by_question:
			final_submission = coding_by_question[qid].get("final_submission") or {}
			passed = _to_int(final_submission.get("passed_test_cases"), default=0)
			total = _to_int(final_submission.get("total_test_cases"), default=0)
			if total > 0 and passed == total:
				return max_score
		return 0

	if expected is None:
		return 0

	# Numeric: exact numeric equality => 1, else 0.
	if qtype == "numeric":
		try:
			return 1 if float(candidate) == float(expected) else 0
		except (TypeError, ValueError):
			return 0

	# Text-like single-answer types: strict normalized equality => 1, else 0.
	if qtype in {"mcq", "short", "long", "fib"}:
		expected_text = _normalize_text(expected)
		candidate_text = _normalize_text(candidate)
		if expected_text and candidate_text and expected_text == candidate_text:
			return 1

	# Option-letter mapping support for MCQ (e.g., "a" => option text).
	if isinstance(expected, str):
		expected_text = _normalize_text(expected)
		candidate_text = _normalize_text(candidate)

		if expected_text in {"a", "b", "c", "d"}:
			options = payload.get("options") if isinstance(payload.get("options"), list) else []
			if not options:
				options = source_payload.get("options") if isinstance(source_payload.get("options"), list) else []
			idx = ord(expected_text) - ord("a")
			if 0 <= idx < len(options):
				mapped = _normalize_text(options[idx])
				if mapped and mapped == candidate_text:
					return 1

	# MSQ: compare normalized set equality => 1, else 0.
	if qtype == "msq" or isinstance(expected, list):
		expected_set = set(_normalize_answer_list(expected))
		if isinstance(candidate, list):
			candidate_set = set(_normalize_answer_list(candidate))
		else:
			candidate_set = set(_normalize_answer_list(candidate))
		if expected_set and expected_set == candidate_set:
			return 1

	# Fallback: compare normalized scalar answers => 1, else 0.
	if _normalize_text(candidate) and _normalize_text(candidate) == _normalize_text(expected):
		return 1

	return 0


def _sum_scores(rows: list[dict[str, Any]]) -> int:
	total = 0
	for row in rows:
		score = row.get("score")
		if score is None:
			continue
		total += max(0, _to_int(score))
	return total


def _sum_coding_scores(coding_by_question: dict[int, dict[str, Any]]) -> int:
	total = 0
	for item in coding_by_question.values():
		final_submission = item.get("final_submission") or {}
		score = final_submission.get("score")
		if score is None:
			continue
		total += max(0, _to_int(score))
	return total


def _fetch_coding_activity(conn, attempt_id: int, candidate_id: int, drive_id: int) -> dict[int, dict[str, Any]]:
	rows = conn.execute(
		text(
			"""
			SELECT
				cs.submission_id,
				cs.question_id,
				cs.language,
				cs.source_code,
				cs.status,
				cs.test_results,
				cs.passed_test_cases,
				cs.total_test_cases,
				cs.execution_time_ms,
				cs.memory_used_kb,
				cs.error_message,
				cs.stdout,
				cs.stderr,
				cs.marks_obtained,
				cs.is_final,
				cs.submitted_at,
				cs.executed_at,
				cs.created_at,
				q.section_id,
				q.question_text,
				q.question_type,
				q.marks
			FROM code_submissions cs
			JOIN questions q ON q.question_id = cs.question_id
			WHERE cs.attempt_id = :attempt_id
			  AND cs.candidate_id = :candidate_id
			  AND q.drive_id = :drive_id
			ORDER BY cs.question_id ASC, cs.created_at ASC, cs.submission_id ASC
			"""
		),
		{
			"attempt_id": attempt_id,
			"candidate_id": candidate_id,
			"drive_id": drive_id,
		},
	).mappings().all()

	grouped: dict[int, dict[str, Any]] = {}

	for raw in rows:
		row = dict(raw)
		qid = int(row["question_id"])
		item = grouped.setdefault(
			qid,
			{
				"section_id": row["section_id"],
				"question_id": qid,
				"question_type": row.get("question_type"),
				"question_text": row.get("question_text"),
				"max_score": row.get("marks"),
				"run_count": 0,
				"runs": [],
				"final_submission": None,
			},
		)

		status = str(row.get("status") or "").strip().lower()
		event = {
			"submission_id": row.get("submission_id"),
			"status": row.get("status"),
			"language": row.get("language"),
			"code": row.get("source_code"),
			"execution_time_ms": row.get("execution_time_ms"),
			"memory_used_kb": row.get("memory_used_kb"),
			"passed_test_cases": row.get("passed_test_cases"),
			"total_test_cases": row.get("total_test_cases"),
			"test_results": _json_parse(row.get("test_results")),
			"stdout": row.get("stdout"),
			"stderr": row.get("stderr"),
			"error_message": row.get("error_message"),
			"score": row.get("marks_obtained"),
			"submitted_at": row.get("submitted_at"),
			"executed_at": row.get("executed_at"),
			"created_at": row.get("created_at"),
		}

		if status == "run":
			item["run_count"] += 1
			item["runs"].append(event)

		if status in {"submitted", "final"} or bool(row.get("is_final")):
			item["final_submission"] = event

	# Fallback: if no explicit final submission row, use latest row per question.
	for qid, item in grouped.items():
		if item["final_submission"] is not None:
			continue
		latest_row = conn.execute(
			text(
				"""
				SELECT
					cs.submission_id,
					cs.status,
					cs.language,
					cs.source_code,
					cs.execution_time_ms,
					cs.memory_used_kb,
					cs.passed_test_cases,
					cs.total_test_cases,
					cs.test_results,
					cs.stdout,
					cs.stderr,
					cs.error_message,
					cs.marks_obtained,
					cs.submitted_at,
					cs.executed_at,
					cs.created_at
				FROM code_submissions cs
				WHERE cs.attempt_id = :attempt_id
				  AND cs.question_id = :question_id
				  AND cs.candidate_id = :candidate_id
				ORDER BY cs.created_at DESC, cs.submission_id DESC
				LIMIT 1
				"""
			),
			{
				"attempt_id": attempt_id,
				"question_id": qid,
				"candidate_id": candidate_id,
			},
		).mappings().first()
		if latest_row:
			lr = dict(latest_row)
			item["final_submission"] = {
				"submission_id": lr.get("submission_id"),
				"status": lr.get("status"),
				"language": lr.get("language"),
				"code": lr.get("source_code"),
				"execution_time_ms": lr.get("execution_time_ms"),
				"memory_used_kb": lr.get("memory_used_kb"),
				"passed_test_cases": lr.get("passed_test_cases"),
				"total_test_cases": lr.get("total_test_cases"),
				"test_results": _json_parse(lr.get("test_results")),
				"stdout": lr.get("stdout"),
				"stderr": lr.get("stderr"),
				"error_message": lr.get("error_message"),
				"score": lr.get("marks_obtained"),
				"submitted_at": lr.get("submitted_at"),
				"executed_at": lr.get("executed_at"),
				"created_at": lr.get("created_at"),
			}

	return grouped


def generate_candidate_exam_report(email: str, launch_code: str, output_path: str | None = None) -> dict[str, Any]:
	"""
	Build one JSON report for a candidate exam using email + launch code.

	Includes:
	- user details and exam details
	- exam mode flags (jit / llm_morphed)
	- exam questions and candidate answers with score
	- morphed questions for llm variant exams
	- coding run history and final submitted code
	"""
	root = Path(__file__).resolve().parents[1]
	_load_env_file(root / ".env")

	database_url = os.getenv("DATABASE_URL")
	if not database_url:
		raise RuntimeError("DATABASE_URL was not found in environment or .env")

	engine = create_engine(database_url, pool_pre_ping=True)

	attempt_ids: list[int] = []
	resolved_email = email
	with engine.connect() as conn:
		base = _resolve_candidate_and_launch(conn, email=email, launch_code=launch_code)
		candidate_id = int(base["candidate_id"])
		drive_id = int(base["drive_id"])
		resolved_email = str(base.get("email") or email)

		exam = _resolve_exam(conn, drive_id)
		attempt_resolution = _resolve_attempt(conn, candidate_id, drive_id)
		selected_attempt = attempt_resolution["selected_attempt"]
		selected_attempt_id = _to_int(selected_attempt.get("attempt_id"), default=0) if selected_attempt else 0

		sections = _fetch_sections(conn, drive_id)
		attempt_ids = [int(a["attempt_id"]) for a in attempt_resolution["all_attempts"] if a.get("attempt_id") is not None]

		attempt_artifacts: dict[int, dict[str, Any]] = {}
		exam_generation_mode = str(exam.get("generation_mode") or "static").strip().lower()
		for attempt_row in attempt_resolution["all_attempts"]:
			attempt_id = _to_int(attempt_row.get("attempt_id"), default=0)
			if attempt_id <= 0:
				continue

			static_questions = _fetch_static_questions_with_answers(conn, attempt_id, drive_id)
			jit_events = _fetch_jit_events(conn, attempt_id)
			jit_final_reports = _fetch_jit_final_reports(conn, attempt_id)
			llm_variants_raw = _fetch_llm_variants(conn, candidate_id, drive_id, attempt_id)
			coding_by_question = _fetch_coding_activity(conn, attempt_id, candidate_id, drive_id)
			include_llm_breakdown = bool(llm_variants_raw) or exam_generation_mode in {"morphing", "llm_morphing"}

			# Attempt -> Section -> Morphed Question -> Evaluate -> Marks
			llm_variants: list[dict[str, Any]] = []
			llm_section_breakdown: list[dict[str, Any]] = []
			for sec in sections:
				section_id = _to_int(sec.get("section_id"), default=0)
				section_rows = [r for r in llm_variants_raw if _to_int(r.get("section_id"), default=0) == section_id]
				effective_rows = _dedupe_llm_variants_by_source(section_rows)

				for variant in effective_rows:
					if variant.get("score") is None:
						variant["score"] = _score_llm_variant(variant, coding_by_question)

				section_marks = _sum_scores(effective_rows)
				section_total_marks = sum(_llm_variant_total_marks(v) for v in effective_rows)
				if include_llm_breakdown:
					llm_section_breakdown.append(
						{
							"section_id": section_id,
							"section_title": sec.get("title"),
							"raw_morphed_question_count": len(section_rows),
							"effective_morphed_question_count": len(effective_rows),
							"llm_morphed_marks": section_marks,
							"llm_morphed_total_marks": section_total_marks,
						}
					)
				llm_variants.extend(effective_rows)

			regular_total = _sum_scores(static_questions)
			llm_total = _sum_scores(llm_variants)
			llm_total_possible = sum(_llm_variant_total_marks(v) for v in llm_variants)
			jit_total = sum(max(0, _to_int(item.get("score"))) for item in jit_events)
			coding_total = _sum_coding_scores(coding_by_question)

			# For morphing attempts, prefer llm_total to avoid counting source+variant twice.
			computed_total = llm_total + jit_total + coding_total if llm_variants else regular_total + jit_total + coding_total

			attempt_row["computed_total_marks"] = computed_total
			attempt_row["computed_breakdown"] = {
				"regular_marks": regular_total,
				"llm_morphed_marks": llm_total,
				"jit_marks": jit_total,
				"coding_marks": coding_total,
			}
			if exam_generation_mode == "jit":
				attempt_row["llm_section_breakdown"] = []
			else:
				attempt_row["llm_section_breakdown"] = llm_section_breakdown if include_llm_breakdown else []
			attempt_row["jit_topic_strength"] = jit_final_reports
			if exam_generation_mode == "jit":
				attempt_row["llm_raw_question_count"] = 0
				attempt_row["llm_effective_question_count"] = 0
				attempt_row["llm_morphed_total_marks"] = None
				attempt_row["llm_morphed_current_score"] = None
				attempt_row["llm_morphed_result"] = ""
			else:
				attempt_row["llm_raw_question_count"] = len(llm_variants_raw)
				attempt_row["llm_effective_question_count"] = len(llm_variants)
				attempt_row["llm_morphed_total_marks"] = llm_total_possible
				attempt_row["llm_morphed_current_score"] = llm_total
				attempt_row["llm_morphed_result"] = "pass" if llm_total_possible > 0 and llm_total >= llm_total_possible else "fail"

			attempt_artifacts[attempt_id] = {
				"static_questions": static_questions,
				"jit_events": jit_events,
				"llm_variants": llm_variants,
				"coding_by_question": coding_by_question,
			}

		if selected_attempt is None:
			result = {
				"input": {"email": email, "launch_code": launch_code},
				"user_details": {
					"user_id": base["user_id"],
					"candidate_id": base["candidate_id"],
					"full_name": base["full_name"],
					"email": base["email"],
					"mobile_no": base["mobile_no"],
					"country": base["country"],
					"timezone": base["timezone"],
					"photo_url": base["photo_url"],
					"years_of_experience": base["years_of_experience"],
					"onboarding_step": base["onboarding_step"],
					"is_active": base["is_active"],
					"email_verified": base["email_verified"],
				},
				"exam_details": exam,
				"exam_mode": {
					"generation_mode": str(exam.get("generation_mode") or "static").lower(),
					"is_jit_exam": str(exam.get("generation_mode") or "").lower() == "jit",
					"is_llm_morphed_exam": False,
				},
				"launch_code_details": {
					"launch_id": base["launch_id"],
					"registration_id": base["registration_id"],
					"drive_id": base["drive_id"],
					"launch_code": base["launch_code"],
					"expires_at": base["expires_at"],
					"used_at": base["used_at"],
					"created_at": base["launch_created_at"],
				},
				"attempt": {
					"selected_attempt": None,
					"all_attempts": attempt_resolution["all_attempts"],
				},
				"sections": sections,
				"questions": {
					"regular_questions": [],
					"jit_questions": [],
					"llm_morphed_questions": [],
					"coding_questions": [],
				},
			}
		else:
			attempt_id = int(selected_attempt["attempt_id"])
			selected_attempt = next(
				(a for a in attempt_resolution["all_attempts"] if _to_int(a.get("attempt_id")) == attempt_id),
				selected_attempt,
			)
			selected_artifacts = attempt_artifacts.get(attempt_id, {})
			static_questions = selected_artifacts.get("static_questions", [])
			jit_events = selected_artifacts.get("jit_events", [])
			llm_variants = selected_artifacts.get("llm_variants", [])
			coding_by_question = selected_artifacts.get("coding_by_question", {})

			generation_mode = str(exam.get("generation_mode") or "static").lower()
			is_jit_exam = generation_mode == "jit" or len(jit_events) > 0
			is_llm_morphed_exam = len(llm_variants) > 0
			if is_jit_exam:
				llm_summary_total_marks = None
				llm_summary_current_score = None
				llm_summary_result = ""
			else:
				llm_summary_total_marks = _to_int(selected_attempt.get("llm_morphed_total_marks"), default=0)
				llm_summary_current_score = _to_int(selected_attempt.get("llm_morphed_current_score"), default=0)
				llm_summary_result = selected_attempt.get("llm_morphed_result", "fail")

			exam_max_marks_value = _to_int(exam.get("max_marks"), default=100)
			selected_total_marks_value = _to_int(selected_attempt.get("computed_total_marks"), default=0)
			final_decision = "pass" if selected_total_marks_value >= exam_max_marks_value else "fail"

			result = {
				"input": {"email": email, "launch_code": launch_code},
				"user_details": {
					"user_id": base["user_id"],
					"candidate_id": base["candidate_id"],
					"full_name": base["full_name"],
					"email": base["email"],
					"mobile_no": base["mobile_no"],
					"country": base["country"],
					"timezone": base["timezone"],
					"photo_url": base["photo_url"],
					"years_of_experience": base["years_of_experience"],
					"onboarding_step": base["onboarding_step"],
					"is_active": base["is_active"],
					"email_verified": base["email_verified"],
				},
				"exam_details": exam,
				"exam_mode": {
					"generation_mode": generation_mode,
					"is_jit_exam": is_jit_exam,
					"is_llm_morphed_exam": is_llm_morphed_exam,
				},
				"launch_code_details": {
					"launch_id": base["launch_id"],
					"registration_id": base["registration_id"],
					"drive_id": base["drive_id"],
					"launch_code": base["launch_code"],
					"expires_at": base["expires_at"],
					"used_at": base["used_at"],
					"created_at": base["launch_created_at"],
				},
				"attempt": {
					"selected_attempt": selected_attempt,
					"all_attempts": attempt_resolution["all_attempts"],
				},
				"sections": sections,
				"questions": {
					"regular_questions": static_questions,
					"jit_questions": jit_events,
					"llm_morphed_questions": llm_variants,
					"coding_questions": list(coding_by_question.values()),
				},
				"summary": {
					"exam_max_marks": exam_max_marks_value,
					"regular_question_count": len(static_questions),
					"jit_question_count": len(jit_events),
					"llm_morphed_question_count": len(llm_variants),
					"coding_question_count": len(coding_by_question),
					"selected_attempt_computed_total_marks": selected_total_marks_value,
					"llm_morphed_total_marks": llm_summary_total_marks,
					"llm_morphed_current_score": llm_summary_current_score,
					"llm_morphed_result": llm_summary_result,
					"final_decision": final_decision,
				},
			}

	# Add top-level JIT final reports if available (for JIT-enabled exams)
	if is_jit_exam and selected_attempt_id > 0 and selected_attempt:
		# Extract final_report from selected attempt's jit_topic_strength
		jit_reports_data = {}
		jit_topic_strength = selected_attempt.get("jit_topic_strength", {})
		if isinstance(jit_topic_strength, dict):
			for section_id, section_data in jit_topic_strength.items():
				if isinstance(section_data, dict) and section_data.get("final_report"):
					jit_reports_data[str(section_id)] = section_data["final_report"]
		if jit_reports_data:
			result["jit_final_reports"] = jit_reports_data

	evidence_frames = _collect_supabase_evidence(
		email=resolved_email,
		selected_attempt_id=selected_attempt_id,
		drive_id=drive_id,
		identifier_candidates=[
			drive_id,
			base.get("drive_id"),
			base.get("launch_id"),
			base.get("registration_id"),
		],
		start_time=selected_attempt.get("start_time") if selected_attempt else None,
		end_time=selected_attempt.get("end_time") if selected_attempt else None,
	)
	logs_info = _collect_supabase_logs(email=resolved_email, selected_attempt_id=selected_attempt_id)
	result["proctoring_artifacts"] = {
		"evidence_frames": evidence_frames,
		"logs": logs_info,
	}

	if output_path:
		output = Path(output_path)
		output.write_text(
			json.dumps(result, indent=2, ensure_ascii=False, default=_json_default),
			encoding="utf-8",
		)
		evidence_manifest_path = _write_evidence_manifest_file(output, evidence_frames)
		result["proctoring_artifacts"]["evidence_frames_json_path"] = evidence_manifest_path

	return result


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Generate candidate exam JSON report from email + launch code")
	parser.add_argument("--email", required=True, help="Candidate email")
	parser.add_argument("--launch-code", required=True, help="Exam launch code")
	parser.add_argument("--output", default="candidate_exam_report.json", help="Output JSON file path")
	return parser.parse_args()


def main() -> int:
	args = _parse_args()
	report = generate_candidate_exam_report(
		email=args.email,
		launch_code=args.launch_code,
		output_path=args.output,
	)
	# print(json.dumps(report, indent=2, ensure_ascii=False, default=_json_default))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

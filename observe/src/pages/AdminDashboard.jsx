import React, { useState, useEffect, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { BACKEND_URL } from '../contexts/BackendContext';
import { ResponsiveContainer, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import {
    LayoutDashboard, FileText, Database, Users, Activity,
    BarChart3, Award, Send, Settings, ShieldCheck,
    LogOut, ChevronRight, Menu, CreditCard, Network, FileSpreadsheet,
    Plus, Search, Filter, MoreVertical, Edit2, Trash2, X, Layers, Code, AlignLeft, CheckSquare, List,
    Mail, UploadCloud, Eye, AlertTriangle, Monitor, PlayCircle, PauseCircle,
    Download, CheckCircle2, TrendingUp, PieChart, ArrowUpRight, ArrowDownRight,
    Megaphone, Clock, Save, Globe, Lock,
    FileArchive, Webhook, Link2, DownloadCloud, CheckCircle, Bell, Copy, Brain, Server, ArrowLeft, Layout, History, Info
} from 'lucide-react';

const API_BASE_URL = BACKEND_URL;

const QUESTION_MORPHING_STRATEGIES = [
    { value: 'rephrase', label: 'Rephrase', description: 'Rewrites wording while preserving core logic and expected answer.' },
    { value: 'contextual', label: 'Contextual', description: 'Changes scenario/domain context while keeping the underlying concept.' },
    { value: 'distractor', label: 'Distractor', description: 'Improves or adds confusing options to better test precision.' },
    { value: 'structural', label: 'Structural', description: 'Changes question structure/format without changing intent.' },
    { value: 'difficulty', label: 'Difficulty', description: 'Adjusts complexity up or down while staying in the same topic.' },
];

const CODING_MORPHING_STRATEGIES = [
    { value: 'code_rephrase', label: 'Code Rephrase', description: 'Rewords the coding prompt without changing required solution behavior.' },
    { value: 'code_contextual', label: 'Code Contextual', description: 'Moves the coding problem into a different real-world scenario.' },
    { value: 'code_difficulty', label: 'Code Difficulty', description: 'Raises or lowers complexity constraints for the same coding intent.' },
    { value: 'code_constraint', label: 'Code Constraint', description: 'Adds implementation constraints such as memory or operation limits.' },
    { value: 'code_tcgen', label: 'Code TCGen', description: 'Generates additional test cases to improve coverage.' },
    { value: 'code_tcscale', label: 'Code TCScale', description: 'Scales test case sizes and edge ranges for robustness checks.' },
];

const JIT_SECTION_QUESTION_TYPES = [
    { value: 'mcq', label: 'MCQ' },
    { value: 'msq', label: 'MSQ' },
    { value: 'fib', label: 'Fill In The Blanks' },
    { value: 'numerical', label: 'Numerical' },
    { value: 'short', label: 'Short Answer' },
    { value: 'long', label: 'Long Answer' },
    { value: 'coding', label: 'Coding' },
    { value: 'mixed', label: 'Mixed' },
];

// --- Placeholder Views ---
const PlaceholderView = ({ title, icon: Icon }) => (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="h-full flex flex-col items-center justify-center text-center p-10 bg-white border border-gray-200/60 rounded-[2rem] shadow-sm">
        <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center mb-6 border border-gray-100">
            <Icon className="w-8 h-8 text-indigo-500" />
        </div>
        <h2 className="text-2xl font-medium text-gray-900 mb-2">{title}</h2>
        <p className="text-gray-500 font-medium max-w-sm">This module is currently under active development. Configuration options and data tables will appear here.</p>
    </motion.div>
);

// --- View 1: Organization Dash (Overview) ---
const Overview = () => {
    const chartData = [
        { name: 'Jan', participants: 4000, completions: 2400 },
        { name: 'Feb', participants: 3000, completions: 1398 },
        { name: 'Mar', participants: 2000, completions: 9800 },
        { name: 'Apr', participants: 2780, completions: 3908 },
        { name: 'May', participants: 1890, completions: 4800 },
        { name: 'Jun', participants: 2390, completions: 3800 },
        { name: 'Jul', participants: 3490, completions: 4300 },
    ];

    return (
        <div className="space-y-6">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-gray-900">Organization Dashboard</h1>
                <p className="text-gray-500 font-medium mt-1">Platform overview and real-time metrics.</p>
            </div>

            {/* Quick Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                    { label: "Total Candidate Registrations", value: "14,239", trend: "+12%", trendUp: true },
                    { label: "Active/Running Exams", value: "3", trend: "Steady", trendUp: true },
                    { label: "Total Exams Created", value: "128", trend: "+4 this week", trendUp: true },
                    { label: "Total Completed Exams", value: "48,912", trend: "+2,100", trendUp: true },
                ].map((stat, i) => (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
                        key={i} className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm"
                    >
                        <p className="text-sm font-bold text-gray-500 mb-2 uppercase tracking-wide">{stat.label}</p>
                        <div className="flex items-end justify-between">
                            <h3 className="text-3xl font-black text-gray-900">{stat.value}</h3>
                            <span className={`text-sm font-bold ${stat.trendUp ? 'text-emerald-600' : 'text-amber-500'}`}>
                                {stat.trend}
                            </span>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Main Content Split */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
                {/* Chart Area (Placeholder) */}
                <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }} className="lg:col-span-2 bg-white p-6 rounded-2xl border border-gray-200 shadow-sm min-h-[400px] flex flex-col">
                    <div className="flex justify-between items-center mb-6">
                        <h3 className="text-lg font-bold text-gray-900">Candidate Participation</h3>
                        <select className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 font-medium text-gray-700 outline-none">
                            <option>Last 30 Days</option>
                            <option>Last Quarter</option>
                        </select>
                    </div>
                    <div className="flex-1 rounded-xl bg-white flex items-center justify-center pt-4">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="colorParticipants" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6b7280' }} dy={10} />
                                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6b7280' }} />
                                <Tooltip 
                                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)' }}
                                    cursor={{ stroke: '#e5e7eb', strokeWidth: 2, strokeDasharray: '3 3' }}
                                />
                                <Area type="monotone" dataKey="participants" stroke="#4f46e5" strokeWidth={3} fillOpacity={1} fill="url(#colorParticipants)" activeDot={{ r: 6, strokeWidth: 0, fill: '#4f46e5' }} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>

                {/* System Activity Feed */}
                <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 }} className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col">
                    <h3 className="text-lg font-bold text-gray-900 mb-6">System Activity</h3>
                    <div className="flex-1 overflow-y-auto pr-2 space-y-6 scrollbar-hide">
                        {[
                            { time: "10m ago", action: "Exam Published", detail: "Q3 Software Engineer Assessment", user: "Admin Sarah" },
                            { time: "1h ago", action: "Bulk Invite Sent", detail: "Invited 450 candidates via CSV", user: "Admin John" },
                            { time: "3h ago", action: "Flag Raised", detail: "Suspicious activity detected in Exam #1042", user: "System", alert: true },
                            { time: "5h ago", action: "Section Added", detail: "Added 'Advanced Algorithms' to Tech Stack", user: "Admin Sarah" },
                        ].map((event, i) => (
                            <div key={i} className="flex gap-4">
                                <div className="w-2 h-2 mt-2 rounded-full shrink-0 bg-indigo-500 ring-4 ring-indigo-50"></div>
                                <div>
                                    <p className="text-sm font-bold text-gray-900">{event.action}</p>
                                    <p className={`text-sm font-medium mt-0.5 ${event.alert ? 'text-red-600' : 'text-gray-500'}`}>{event.detail}</p>
                                    <p className="text-xs font-bold text-gray-400 mt-1 uppercase tracking-wider">{event.time} • {event.user}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                    <button className="w-full mt-4 py-2 border border-gray-200 rounded-xl text-sm font-bold text-gray-900 hover:bg-gray-50 transition-colors">
                        View Full Audit Log
                    </button>
                </motion.div>
            </div>
        </div>
    );
};

// --- View 2: Exam Management ---
const ExamManagement = () => {
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);

    // Advanced Exam Features State
    const [isJitEnabled, setIsJitEnabled] = useState(false);
    const [isMorphingEnabled, setIsMorphingEnabled] = useState(true);
    const [publishNow, setPublishNow] = useState(false);
    const [jitSections, setJitSections] = useState([{ id: 1, topic: '', count: 10, question_type: 'mcq' }]);
    const [editingExamId, setEditingExamId] = useState(null);

    const [exams, setExams] = useState([]);
    const [loadingExams, setLoadingExams] = useState(true);
    const [examError, setExamError] = useState('');
    const [createError, setCreateError] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [topicInput, setTopicInput] = useState('');
    const [specializationInput, setSpecializationInput] = useState('');

    const [examForm, setExamForm] = useState({
        title: '',
        exam_type: 'Recruitment',
        duration_minutes: 60,
        max_attempts: 1,
        description: '',
        eligibility: '',
        start_date: '',
        end_date: '',
        exam_date: '',
        max_marks: '',
        key_topics: [],
        specializations: [],
    });

    const addUniqueTag = (list, value) => {
        const normalized = String(value || '').trim();
        if (!normalized) {
            return list;
        }
        if (list.some((item) => item.toLowerCase() === normalized.toLowerCase())) {
            return list;
        }
        return [...list, normalized];
    };

    const addTopic = () => {
        setExamForm((prev) => ({ ...prev, key_topics: addUniqueTag(prev.key_topics || [], topicInput) }));
        setTopicInput('');
    };

    const addSpecialization = () => {
        setExamForm((prev) => ({ ...prev, specializations: addUniqueTag(prev.specializations || [], specializationInput) }));
        setSpecializationInput('');
    };

    const removeTopic = (topic) => {
        setExamForm((prev) => ({
            ...prev,
            key_topics: (prev.key_topics || []).filter((item) => item !== topic),
        }));
    };

    const removeSpecialization = (specialization) => {
        setExamForm((prev) => ({
            ...prev,
            specializations: (prev.specializations || []).filter((item) => item !== specialization),
        }));
    };

    useEffect(() => {
        const loadExams = async () => {
            const adminToken = localStorage.getItem('admin_token');
            if (!adminToken) {
                setExamError('Admin session expired. Please log in again.');
                setLoadingExams(false);
                return;
            }

            try {
                setLoadingExams(true);
                setExamError('');

                const res = await fetch(`${API_BASE_URL}/admin/exams`, {
                    headers: {
                        Authorization: `Bearer ${adminToken}`,
                    },
                });

                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(data?.detail || 'Failed to load exams');
                }

                setExams(data.exams || []);
            } catch (error) {
                setExamError(error.message || 'Unable to load exams.');
            } finally {
                setLoadingExams(false);
            }
        };

        loadExams();
    }, []);

    const addJitSection = () => {
        setJitSections([...jitSections, { id: Date.now(), topic: '', count: 10, question_type: 'mcq' }]);
    };

    const updateJitSection = (id, field, value) => {
        setJitSections(jitSections.map(s => s.id === id ? { ...s, [field]: value } : s));
    };

    const removeJitSection = (id) => {
        setJitSections(jitSections.filter(s => s.id !== id));
    };

    const resetExamForm = () => {
        setExamForm({
            title: '',
            exam_type: 'Recruitment',
            duration_minutes: 60,
            max_attempts: 1,
            description: '',
            eligibility: '',
            start_date: '',
            end_date: '',
            exam_date: '',
            max_marks: '',
            key_topics: [],
            specializations: [],
        });
        setIsJitEnabled(false);
        setIsMorphingEnabled(true);
        setPublishNow(false);
        setEditingExamId(null);
        setJitSections([{ id: 1, topic: '', count: 10, question_type: 'mcq' }]);
        setTopicInput('');
        setSpecializationInput('');
        setCreateError('');
    };

    const openEditExamModal = async (exam) => {
        setEditingExamId(exam.exam_id);
        setExamForm({
            title: exam.title || '',
            exam_type: exam.exam_type || 'Recruitment',
            duration_minutes: exam.duration_minutes || 60,
            max_attempts: exam.max_attempts || 1,
            description: exam.description || '',
            eligibility: exam.eligibility || '',
            start_date: exam.start_date || '',
            end_date: exam.end_date || '',
            exam_date: exam.exam_date ? String(exam.exam_date).slice(0, 16) : '',
            max_marks: exam.max_marks ?? '',
            key_topics: Array.isArray(exam.key_topics) ? exam.key_topics : [],
            specializations: Array.isArray(exam.specializations) ? exam.specializations : [],
        });
        setPublishNow(Boolean(exam.is_published));
        const mode = String(exam.generation_mode || 'static').trim().toLowerCase().replace('-', '_');
        const isJit = mode === 'jit';
        const isMorphing = mode === 'morphing' || mode === 'llm_morphing';
        setIsJitEnabled(isJit);
        setIsMorphingEnabled(isMorphing);
        setCreateError('');

        if (isJit) {
            const adminToken = localStorage.getItem('admin_token');
            if (!adminToken) {
                setCreateError('Admin session expired. Please log in again.');
                return;
            }

            try {
                const res = await fetch(`${API_BASE_URL}/admin/exams/${exam.exam_id}/sections`, {
                    headers: {
                        Authorization: `Bearer ${adminToken}`,
                    },
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(data?.detail || 'Failed to load JIT sections');
                }

                const fetchedSections = (data.sections || []).map((section, index) => ({
                    id: section.section_id || Date.now() + index,
                    topic: section.title || '',
                    count: Number(section.planned_question_count || 0) || 1,
                    question_type: String(section.question_type || 'mcq').toLowerCase(),
                }));

                if (fetchedSections.length > 0) {
                    setJitSections(fetchedSections);
                } else {
                    setJitSections([{ id: 1, topic: '', count: 10, question_type: 'mcq' }]);
                }
            } catch (error) {
                setCreateError(error.message || 'Unable to load JIT sections.');
                setJitSections([{ id: 1, topic: '', count: 10, question_type: 'mcq' }]);
            }
        } else {
            setJitSections([{ id: 1, topic: '', count: 10, question_type: 'mcq' }]);
        }

        setIsEditModalOpen(true);
    };

    const handleDeleteExam = async (examId) => {
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            setExamError('Admin session expired. Please log in again.');
            return;
        }

        const confirmed = window.confirm(`Delete exam EX-${examId}? This will permanently remove exam data.`);
        if (!confirmed) {
            return;
        }

        try {
            setExamError('');
            const res = await fetch(`${API_BASE_URL}/admin/exams/${examId}`, {
                method: 'DELETE',
                headers: {
                    Authorization: `Bearer ${adminToken}`,
                },
            });

            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to delete exam');
            }

            setExams((prev) => prev.filter((exam) => exam.exam_id !== examId));
        } catch (error) {
            setExamError(error.message || 'Unable to delete exam.');
        }
    };

    const validateExamForm = () => {
        if (!examForm.eligibility.trim()) {
            setCreateError('Eligibility is required.');
            return false;
        }
        if (!examForm.start_date) {
            setCreateError('Start date is required.');
            return false;
        }
        if (!examForm.end_date) {
            setCreateError('End date is required.');
            return false;
        }
        if (!examForm.exam_date) {
            setCreateError('Exam date and time is required.');
            return false;
        }
        if (new Date(examForm.end_date) < new Date(examForm.start_date)) {
            setCreateError('End date cannot be before start date.');
            return false;
        }
        if (!examForm.max_marks || Number(examForm.max_marks) <= 0) {
            setCreateError('Max marks must be greater than 0.');
            return false;
        }
        return true;
    };

    const getStatusBadge = (status) => {
        const normalized = String(status || 'draft').toLowerCase();
        if (normalized === 'active') {
            return 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20';
        }
        if (normalized === 'completed') {
            return 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-600/20';
        }
        return 'bg-gray-100 text-gray-700 ring-1 ring-gray-500/20';
    };

    const mapGenerationMode = () => {
        if (isJitEnabled) return 'jit';
        if (isMorphingEnabled) return 'morphing';
        return 'static';
    };

    const handleCreateExam = async () => {
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            setCreateError('Admin session expired. Please log in again.');
            return;
        }

        const title = examForm.title.trim();
        if (!title) {
            setCreateError('Exam title is required.');
            return;
        }

        if (!examForm.exam_type.trim()) {
            setCreateError('Exam type is required.');
            return;
        }

        if (Number(examForm.duration_minutes) <= 0) {
            setCreateError('Duration must be greater than 0.');
            return;
        }

        if (Number(examForm.max_attempts) <= 0) {
            setCreateError('Max attempts must be greater than 0.');
            return;
        }

        if (!validateExamForm()) {
            return;
        }

        let normalizedJitSections = [];
        if (isJitEnabled) {
            normalizedJitSections = jitSections.map((section) => ({
                topic: String(section.topic || '').trim(),
                count: Number(section.count),
                question_type: String(section.question_type || 'mcq').trim().toLowerCase(),
            }));

            if (normalizedJitSections.length === 0) {
                setCreateError('At least one JIT section is required.');
                return;
            }

            const hasInvalidSection = normalizedJitSections.some(
                (section) => !section.topic || !Number.isFinite(section.count) || section.count <= 0 || !section.question_type
            );

            if (hasInvalidSection) {
                setCreateError('Each JIT section must have a topic, question type, and question count greater than 0.');
                return;
            }
        }

        try {
            setIsSaving(true);
            setCreateError('');

            const res = await fetch(`${API_BASE_URL}/admin/exams`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${adminToken}`,
                },
                body: JSON.stringify({
                    title,
                    exam_type: examForm.exam_type.trim(),
                    duration_minutes: Number(examForm.duration_minutes),
                    max_attempts: Number(examForm.max_attempts),
                    description: examForm.description.trim(),
                    generation_mode: mapGenerationMode(),
                    jit_sections: isJitEnabled ? normalizedJitSections : null,
                    eligibility: examForm.eligibility.trim() || null,
                    start_date: examForm.start_date || null,
                    end_date: examForm.end_date || null,
                    exam_date: examForm.exam_date || null,
                    max_marks: examForm.max_marks ? Number(examForm.max_marks) : null,
                    key_topics: examForm.key_topics || [],
                    specializations: examForm.specializations || [],
                    is_published: publishNow,
                }),
            });

            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to create exam');
            }

            if (data.exam) {
                setExams((prev) => [data.exam, ...prev]);
            }

            setIsCreateModalOpen(false);
            resetExamForm();
        } catch (error) {
            setCreateError(error.message || 'Unable to create exam.');
        } finally {
            setIsSaving(false);
        }
    };

    const handleUpdateExam = async () => {
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            setCreateError('Admin session expired. Please log in again.');
            return;
        }

        if (!editingExamId) {
            setCreateError('No exam selected for editing.');
            return;
        }

        const title = examForm.title.trim();
        if (!title) {
            setCreateError('Exam title is required.');
            return;
        }
        if (!examForm.exam_type.trim()) {
            setCreateError('Exam type is required.');
            return;
        }
        if (Number(examForm.duration_minutes) <= 0) {
            setCreateError('Duration must be greater than 0.');
            return;
        }
        if (Number(examForm.max_attempts) <= 0) {
            setCreateError('Max attempts must be greater than 0.');
            return;
        }
        if (!validateExamForm()) {
            return;
        }

        try {
            setIsSaving(true);
            setCreateError('');

            const res = await fetch(`${API_BASE_URL}/admin/exams/${editingExamId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${adminToken}`,
                },
                body: JSON.stringify({
                    title,
                    exam_type: examForm.exam_type.trim(),
                    duration_minutes: Number(examForm.duration_minutes),
                    max_attempts: Number(examForm.max_attempts),
                    description: examForm.description.trim(),
                    generation_mode: mapGenerationMode(),
                    eligibility: examForm.eligibility.trim(),
                    start_date: examForm.start_date,
                    end_date: examForm.end_date,
                    exam_date: examForm.exam_date,
                    max_marks: Number(examForm.max_marks),
                    key_topics: examForm.key_topics || [],
                    specializations: examForm.specializations || [],
                    is_published: publishNow,
                }),
            });

            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to update exam');
            }

            setExams((prev) =>
                prev.map((exam) =>
                    exam.exam_id === editingExamId
                        ? {
                            ...exam,
                            title,
                            exam_type: examForm.exam_type.trim(),
                            duration_minutes: Number(examForm.duration_minutes),
                            max_attempts: Number(examForm.max_attempts),
                            description: examForm.description.trim(),
                            generation_mode: mapGenerationMode(),
                            eligibility: examForm.eligibility.trim(),
                            start_date: examForm.start_date,
                            end_date: examForm.end_date,
                            exam_date: examForm.exam_date,
                            max_marks: Number(examForm.max_marks),
                            key_topics: examForm.key_topics || [],
                            specializations: examForm.specializations || [],
                            is_published: publishNow,
                            status: publishNow ? 'saved' : 'draft',
                        }
                        : exam
                )
            );

            setIsEditModalOpen(false);
            resetExamForm();
        } catch (error) {
            setCreateError(error.message || 'Unable to update exam.');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="space-y-6 h-full flex flex-col">
            {/* Header & Actions */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Exam Management</h1>
                    <p className="text-gray-500 font-medium mt-1">Create, configure, and monitor assessments.</p>
                </div>
                <button
                    onClick={() => {
                        resetExamForm();
                        setIsCreateModalOpen(true);
                    }}
                    className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-sm"
                >
                    <Plus className="w-4 h-4" /> Create Exam
                </button>
            </div>

            {/* Toolbar (Search & Filters) */}
            <div className="flex flex-col sm:flex-row gap-3 bg-white p-2 rounded-2xl border border-gray-200 shadow-sm">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search exams by title or ID..."
                        className="w-full pl-9 pr-4 py-2 bg-gray-50 border-none rounded-xl focus:ring-1 focus:ring-indigo-500 font-medium text-sm text-gray-900 outline-none"
                    />
                </div>
                <button className="flex items-center gap-2 px-4 py-2 bg-gray-50 text-gray-600 border border-gray-100 rounded-xl font-medium text-sm hover:bg-gray-100 transition-colors">
                    <Filter className="w-4 h-4" /> Filters
                </button>
            </div>

            {/* Data Table */}
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex-1 overflow-hidden flex flex-col">
                <div className="overflow-x-auto scrollbar-hide">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-gray-50/50 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                <th className="p-4 pl-6 font-bold">Exam Details</th>
                                <th className="p-4 font-bold">Type</th>
                                <th className="p-4 font-bold">Duration</th>
                                <th className="p-4 font-bold">Sections</th>
                                <th className="p-4 font-bold">Publish</th>
                                <th className="p-4 font-bold">Status</th>
                                <th className="p-4 pr-6 text-right font-bold">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {exams.map((exam, i) => (
                                <motion.tr
                                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                                    key={exam.exam_id} className="hover:bg-gray-50/50 transition-colors group"
                                >
                                    <td className="p-4 pl-6">
                                        <p className="font-bold text-sm text-gray-900">{exam.title}</p>
                                        <p className="text-xs font-medium text-gray-400 mt-0.5">EX-{exam.exam_id}</p>
                                    </td>
                                    <td className="p-4 text-sm font-medium text-gray-600">{exam.exam_type || 'N/A'}</td>
                                    <td className="p-4 text-sm font-medium text-gray-600">{exam.duration_minutes || 0} mins</td>
                                    <td className="p-4 text-sm font-medium text-gray-600">{exam.section_count || 0}</td>
                                    <td className="p-4 text-sm font-bold">
                                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${exam.is_published ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20' : 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20'}`}>
                                            {exam.is_published ? 'Published' : 'Unpublished'}
                                        </span>
                                    </td>
                                    <td className="p-4">
                                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${getStatusBadge(exam.status)}`}>
                                            {exam.status || 'draft'}
                                        </span>
                                    </td>
                                    <td className="p-4 pr-6 text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            <button onClick={() => openEditExamModal(exam)} className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"><Edit2 className="w-4 h-4" /></button>
                                            <button onClick={() => handleDeleteExam(exam.exam_id)} className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"><Trash2 className="w-4 h-4" /></button>
                                            <button className="p-1.5 text-gray-400 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"><MoreVertical className="w-4 h-4" /></button>
                                        </div>
                                    </td>
                                </motion.tr>
                            ))}
                            {!loadingExams && exams.length === 0 && (
                                <tr>
                                    <td colSpan="7" className="p-10 text-center text-gray-500 font-medium">
                                        No exams available. Create your first exam.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
                {/* Pagination (Static for mock) */}
                <div className="p-4 border-t border-gray-100 flex items-center justify-between text-sm text-gray-500 mt-auto bg-gray-50/30">
                    <span className="font-medium">
                        {loadingExams ? 'Loading exams...' : `Showing ${exams.length} exam${exams.length === 1 ? '' : 's'}`}
                    </span>
                    <div className="flex gap-1">
                        <button className="px-3 py-1 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors font-medium">Prev</button>
                        <button className="px-3 py-1 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors font-medium">Next</button>
                    </div>
                </div>
            </div>

            {examError && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                    {examError}
                </div>
            )}

            {/* Create Exam Slide-over Modal */}
            <AnimatePresence>
                {(isCreateModalOpen || isEditModalOpen) && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="fixed inset-0 bg-gray-900/20 backdrop-blur-sm z-50 flex justify-end"
                            onClick={() => { setIsCreateModalOpen(false); setIsEditModalOpen(false); }}
                        >
                            <motion.div
                                initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }} transition={{ type: "spring", damping: 25, stiffness: 200 }}
                                className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col"
                                onClick={e => e.stopPropagation()}
                            >
                                <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                                    <h2 className="text-lg font-bold text-gray-900">{isEditModalOpen ? 'Edit Exam' : 'Create New Exam'}</h2>
                                    <button onClick={() => { setIsCreateModalOpen(false); setIsEditModalOpen(false); }} className="text-gray-400 hover:text-gray-900 p-1 rounded-lg hover:bg-gray-100 transition-colors">
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>
                                <div className="p-6 overflow-y-auto flex-1 space-y-6 scrollbar-hide">

                                    {/* Advanced Toggles */}
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className={`p-4 rounded-xl border transition-all cursor-pointer ${isJitEnabled ? 'bg-indigo-50 border-indigo-200' : 'bg-gray-50 border-gray-100 hover:border-gray-200'}`} onClick={() => { setIsJitEnabled(!isJitEnabled); if (!isJitEnabled) setIsMorphingEnabled(false); }}>
                                            <div className="flex justify-between items-start mb-2">
                                                <div className={`p-1.5 rounded-lg ${isJitEnabled ? 'bg-indigo-100 text-indigo-600' : 'bg-gray-200 text-gray-500'}`}><Brain className="w-4 h-4" /></div>
                                                <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${isJitEnabled ? 'border-indigo-600' : 'border-gray-300'}`}>
                                                    {isJitEnabled && <div className="w-2 h-2 rounded-full bg-indigo-600" />}
                                                </div>
                                            </div>
                                            <h4 className="text-sm font-bold text-gray-900">JIT Gen</h4>
                                            <p className="text-[10px] font-medium text-gray-500 mt-0.5 leading-tight">Generate on the fly</p>
                                        </div>

                                        <div className={`p-4 rounded-xl border transition-all cursor-pointer ${isMorphingEnabled ? 'bg-emerald-50 border-emerald-200' : 'bg-gray-50 border-gray-100 hover:border-gray-200'}`} onClick={() => { setIsMorphingEnabled(!isMorphingEnabled); if (!isMorphingEnabled) setIsJitEnabled(false); }}>
                                            <div className="flex justify-between items-start mb-2">
                                                <div className={`p-1.5 rounded-lg ${isMorphingEnabled ? 'bg-emerald-100 text-emerald-600' : 'bg-gray-200 text-gray-500'}`}><Code className="w-4 h-4" /></div>
                                                <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${isMorphingEnabled ? 'border-emerald-600' : 'border-gray-300'}`}>
                                                    {isMorphingEnabled && <div className="w-2 h-2 rounded-full bg-emerald-600" />}
                                                </div>
                                            </div>
                                            <h4 className="text-sm font-bold text-gray-900">Morphing</h4>
                                            <p className="text-[10px] font-medium text-gray-500 mt-0.5 leading-tight">Dynamic rephrasing</p>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Publish Preference</label>
                                        <div className="grid grid-cols-2 gap-3">
                                            <button type="button" onClick={() => setPublishNow(false)} className={`px-3 py-2 rounded-xl border text-sm font-bold transition-colors ${!publishNow ? 'bg-amber-50 border-amber-300 text-amber-700' : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'}`}>Publish Later</button>
                                            <button type="button" onClick={() => setPublishNow(true)} className={`px-3 py-2 rounded-xl border text-sm font-bold transition-colors ${publishNow ? 'bg-emerald-50 border-emerald-300 text-emerald-700' : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'}`}>Publish Now</button>
                                        </div>
                                    </div>

                                    {/* Main Form Area */}
                                    <div className="pt-4 border-t border-gray-100 space-y-5">
                                        <div>
                                            <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Exam Title</label>
                                            <input
                                                type="text"
                                                value={examForm.title}
                                                onChange={(e) => setExamForm((prev) => ({ ...prev, title: e.target.value }))}
                                                placeholder="e.g. Senior Frontend Assessment"
                                                className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Exam Type</label>
                                            <select
                                                value={examForm.exam_type}
                                                onChange={(e) => setExamForm((prev) => ({ ...prev, exam_type: e.target.value }))}
                                                className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900 bg-white"
                                            >
                                                <option>Recruitment</option>
                                                <option>Certification</option>
                                                <option>University</option>
                                            </select>
                                        </div>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Duration (Mins)</label>
                                                <input
                                                    type="number"
                                                    value={examForm.duration_minutes}
                                                    min="1"
                                                    onChange={(e) => setExamForm((prev) => ({ ...prev, duration_minutes: Number(e.target.value) || 0 }))}
                                                    className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Max Attempts</label>
                                                <input
                                                    type="number"
                                                    value={examForm.max_attempts}
                                                    min="1"
                                                    onChange={(e) => setExamForm((prev) => ({ ...prev, max_attempts: Number(e.target.value) || 0 }))}
                                                    className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                                />
                                            </div>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Description</label>
                                            <textarea
                                                rows={4}
                                                value={examForm.description}
                                                onChange={(e) => setExamForm((prev) => ({ ...prev, description: e.target.value }))}
                                                placeholder="Internal description for this exam..."
                                                className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900 resize-none"
                                            ></textarea>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Eligibility Criteria</label>
                                            <textarea
                                                rows={2}
                                                value={examForm.eligibility}
                                                onChange={(e) => setExamForm((prev) => ({ ...prev, eligibility: e.target.value }))}
                                                placeholder="e.g. Final year students, 60%+ aggregate..."
                                                className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900 resize-none"
                                            ></textarea>
                                        </div>
                                        <div>
                                            <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Specializations</label>
                                            <div className="flex gap-2">
                                                <input
                                                    type="text"
                                                    value={specializationInput}
                                                    onChange={(e) => setSpecializationInput(e.target.value)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') {
                                                            e.preventDefault();
                                                            addSpecialization();
                                                        }
                                                    }}
                                                    placeholder="e.g. Frontend, Data Science"
                                                    className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                                />
                                                <button type="button" onClick={addSpecialization} className="px-3 py-2.5 bg-gray-900 text-white rounded-xl text-sm font-bold hover:bg-gray-800 transition-colors">Add</button>
                                            </div>
                                            {examForm.specializations.length > 0 && (
                                                <div className="mt-2 flex flex-wrap gap-2">
                                                    {examForm.specializations.map((item, idx) => (
                                                        <button key={`${item}-${idx}`} type="button" onClick={() => removeSpecialization(item)} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-bold border border-emerald-200 hover:bg-emerald-100 transition-colors">
                                                            {item} <X className="w-3 h-3" />
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <div>
                                            <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Key Topics</label>
                                            <div className="flex gap-2">
                                                <input
                                                    type="text"
                                                    value={topicInput}
                                                    onChange={(e) => setTopicInput(e.target.value)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') {
                                                            e.preventDefault();
                                                            addTopic();
                                                        }
                                                    }}
                                                    placeholder="e.g. React Hooks, SQL Joins"
                                                    className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                                />
                                                <button type="button" onClick={addTopic} className="px-3 py-2.5 bg-gray-900 text-white rounded-xl text-sm font-bold hover:bg-gray-800 transition-colors">Add</button>
                                            </div>
                                            {examForm.key_topics.length > 0 && (
                                                <div className="mt-2 flex flex-wrap gap-2">
                                                    {examForm.key_topics.map((item, idx) => (
                                                        <button key={`${item}-${idx}`} type="button" onClick={() => removeTopic(item)} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 text-xs font-bold border border-indigo-200 hover:bg-indigo-100 transition-colors">
                                                            {item} <X className="w-3 h-3" />
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Start Date</label>
                                                <input
                                                    type="date"
                                                    value={examForm.start_date}
                                                    onChange={(e) => setExamForm((prev) => ({ ...prev, start_date: e.target.value }))}
                                                    className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">End Date</label>
                                                <input
                                                    type="date"
                                                    value={examForm.end_date}
                                                    onChange={(e) => setExamForm((prev) => ({ ...prev, end_date: e.target.value }))}
                                                    className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                                />
                                            </div>
                                        </div>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Exam Date &amp; Time</label>
                                                <input
                                                    type="datetime-local"
                                                    value={examForm.exam_date}
                                                    onChange={(e) => setExamForm((prev) => ({ ...prev, exam_date: e.target.value }))}
                                                    className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Max Marks</label>
                                                <input
                                                    type="number"
                                                    value={examForm.max_marks}
                                                    min="0"
                                                    onChange={(e) => setExamForm((prev) => ({ ...prev, max_marks: e.target.value }))}
                                                    placeholder="e.g. 100"
                                                    className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                                />
                                            </div>
                                        </div>

                                        {isJitEnabled && (
                                            <div className="space-y-4">
                                                <div className="flex items-center justify-between">
                                                    <h3 className="text-sm font-bold text-gray-900">JIT Sections Configuration</h3>
                                                    <button onClick={addJitSection} type="button" className="text-xs font-bold text-indigo-600 hover:text-indigo-700 bg-indigo-50 px-2.5 py-1.5 rounded-lg transition-colors flex items-center gap-1"><Plus className="w-3 h-3" /> Add Section</button>
                                                </div>
                                                {jitSections.map((sec) => (
                                                    <div key={sec.id} className="p-4 bg-gray-50 border border-gray-100 rounded-xl space-y-3 relative group">
                                                        {jitSections.length > 1 && (
                                                            <button onClick={() => removeJitSection(sec.id)} type="button" className="absolute top-2 right-2 p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors opacity-0 group-hover:opacity-100"><X className="w-4 h-4" /></button>
                                                        )}
                                                        <div>
                                                            <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1 ml-1">Topic Name</label>
                                                            <input type="text" value={sec.topic} onChange={e => updateJitSection(sec.id, 'topic', e.target.value)} placeholder="e.g. React Hooks" className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900" />
                                                        </div>
                                                        <div>
                                                            <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1 ml-1">Question Type</label>
                                                            <select value={sec.question_type || 'mcq'} onChange={e => updateJitSection(sec.id, 'question_type', e.target.value)} className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900 bg-white">
                                                                {JIT_SECTION_QUESTION_TYPES.map((option) => (
                                                                    <option key={option.value} value={option.value}>{option.label}</option>
                                                                ))}
                                                            </select>
                                                        </div>
                                                        <div>
                                                            <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1 ml-1">Number of Questions</label>
                                                            <input type="number" value={sec.count} onChange={e => updateJitSection(sec.id, 'count', e.target.value)} min="1" className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900" />
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        {createError && (
                                            <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
                                                {createError}
                                            </div>
                                        )}
                                    </div>
                                </div>
                                <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3 shrink-0">
                                    <button onClick={() => { setIsCreateModalOpen(false); setIsEditModalOpen(false); }} className="px-4 py-2.5 text-sm font-bold text-gray-600 hover:text-gray-900 transition-colors">Cancel</button>
                                    <button
                                        onClick={isEditModalOpen ? handleUpdateExam : handleCreateExam}
                                        disabled={isSaving}
                                        className="px-5 py-2.5 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
                                    >
                                        {isSaving ? 'Saving...' : isEditModalOpen ? 'Save Changes' : 'Save & Continue'}
                                    </button>
                                </div>
                            </motion.div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
};

// --- View 3: Section Management ---
const SectionManagement = () => {
    const [activeView, setActiveView] = useState('exams');
    const [selectedExamId, setSelectedExamId] = useState(null);
    const [selectedSectionId, setSelectedSectionId] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [isAddSectionModalOpen, setIsAddSectionModalOpen] = useState(false);
    const [isEditSectionModalOpen, setIsEditSectionModalOpen] = useState(false);
    const [editingSection, setEditingSection] = useState(null);
    const [isQuestionModalOpen, setIsQuestionModalOpen] = useState(false);
    const [editingQuestion, setEditingQuestion] = useState(null);
    const [questionType, setQuestionType] = useState('MCQ');
    const [options, setOptions] = useState(['', '', '', '']);
    const [correctAnswer, setCorrectAnswer] = useState('');
    const [correctAnswers, setCorrectAnswers] = useState([]);
    const [taxonomyLevel, setTaxonomyLevel] = useState(3);
    const [morphingStrategy, setMorphingStrategy] = useState('');
    const [timeComplexity, setTimeComplexity] = useState('');
    const [spaceComplexity, setSpaceComplexity] = useState('');
    const [codingTestCases, setCodingTestCases] = useState([{ id: Date.now(), input: '', output: '', visibility: 'visible' }]);
    const [hintInput, setHintInput] = useState('');
    const [keywordTagInput, setKeywordTagInput] = useState('');
    const [forbiddenBuiltinInput, setForbiddenBuiltinInput] = useState('');
    const [codingHints, setCodingHints] = useState([]);
    const [keywordTags, setKeywordTags] = useState([]);
    const [forbiddenBuiltins, setForbiddenBuiltins] = useState([]);

    const [exams, setExams] = useState([]);
    const [sections, setSections] = useState([]);
    const [questions, setQuestions] = useState([]);
    const [loadingExams, setLoadingExams] = useState(true);
    const [loadingSections, setLoadingSections] = useState(false);
    const [loadingQuestions, setLoadingQuestions] = useState(false);
    const [dataError, setDataError] = useState('');
    const [sectionError, setSectionError] = useState('');
    const [questionError, setQuestionError] = useState('');

    const [newSectionForm, setNewSectionForm] = useState({
        title: '',
        section_type: 'Mixed',
    });
    const [editSectionForm, setEditSectionForm] = useState({
        title: '',
        section_type: 'Mixed',
    });

    useEffect(() => {
        const loadExams = async () => {
            const adminToken = localStorage.getItem('admin_token');
            if (!adminToken) {
                setDataError('Admin session expired. Please log in again.');
                setLoadingExams(false);
                return;
            }

            try {
                setLoadingExams(true);
                setDataError('');

                const res = await fetch(`${API_BASE_URL}/admin/exams`, {
                    headers: {
                        Authorization: `Bearer ${adminToken}`,
                    },
                });

                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(data?.detail || 'Failed to load exams');
                }

                setExams(data.exams || []);
            } catch (error) {
                setDataError(error.message || 'Unable to load exams.');
            } finally {
                setLoadingExams(false);
            }
        };

        loadExams();
    }, []);

    useEffect(() => {
        if (!selectedExamId) {
            setSections([]);
            return;
        }

        const loadSections = async () => {
            const adminToken = localStorage.getItem('admin_token');
            if (!adminToken) {
                setDataError('Admin session expired. Please log in again.');
                return;
            }

            try {
                setLoadingSections(true);
                setDataError('');

                const res = await fetch(`${API_BASE_URL}/admin/exams/${selectedExamId}/sections`, {
                    headers: {
                        Authorization: `Bearer ${adminToken}`,
                    },
                });

                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(data?.detail || 'Failed to load sections');
                }

                setSections(data.sections || []);
            } catch (error) {
                setDataError(error.message || 'Unable to load sections.');
            } finally {
                setLoadingSections(false);
            }
        };

        loadSections();
    }, [selectedExamId]);

    useEffect(() => {
        if (!selectedSectionId) {
            setQuestions([]);
            return;
        }

        const loadQuestions = async () => {
            const adminToken = localStorage.getItem('admin_token');
            if (!adminToken) {
                setDataError('Admin session expired. Please log in again.');
                return;
            }

            try {
                setLoadingQuestions(true);
                setDataError('');

                const res = await fetch(`${API_BASE_URL}/admin/exams/sections/${selectedSectionId}/questions`, {
                    headers: {
                        Authorization: `Bearer ${adminToken}`,
                    },
                });

                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(data?.detail || 'Failed to load questions');
                }

                setQuestions(data.questions || []);
            } catch (error) {
                setDataError(error.message || 'Unable to load questions.');
            } finally {
                setLoadingQuestions(false);
            }
        };

        loadQuestions();
    }, [selectedSectionId]);

    const activeExam = exams.find((e) => e.exam_id === selectedExamId);
    const activeSection = sections.find((s) => s.section_id === selectedSectionId);

    const filteredSections = sections.filter(
        (s) => s.title.toLowerCase().includes(searchTerm.toLowerCase())
    );
    const filteredQuestions = questions.filter((q) =>
        q.question_text.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const addUniqueListItem = (setter, currentList, value) => {
        const cleaned = String(value || '').trim();
        if (!cleaned) {
            return;
        }
        if (currentList.some((item) => String(item).toLowerCase() === cleaned.toLowerCase())) {
            return;
        }
        setter([...currentList, cleaned]);
    };

    const removeListItem = (setter, currentList, value) => {
        setter(currentList.filter((item) => item !== value));
    };

    const addCodingTestCase = () => {
        setCodingTestCases((prev) => [...prev, { id: Date.now() + prev.length, input: '', output: '', visibility: 'visible' }]);
    };

    const removeCodingTestCase = (id) => {
        setCodingTestCases((prev) => (prev.length <= 1 ? prev : prev.filter((tc) => tc.id !== id)));
    };

    const updateCodingTestCase = (id, field, value) => {
        setCodingTestCases((prev) => prev.map((tc) => (tc.id === id ? { ...tc, [field]: value } : tc)));
    };

    const resetQuestionEditorState = () => {
        setCorrectAnswer('');
        setCorrectAnswers([]);
        setTaxonomyLevel(3);
        setMorphingStrategy('');
        setTimeComplexity('');
        setSpaceComplexity('');
        setCodingTestCases([{ id: Date.now(), input: '', output: '', visibility: 'visible' }]);
        setHintInput('');
        setKeywordTagInput('');
        setForbiddenBuiltinInput('');
        setCodingHints([]);
        setKeywordTags([]);
        setForbiddenBuiltins([]);
    };

    const openQuestionEditor = (question = null) => {
        if (!question) {
            setEditingQuestion(null);
            setQuestionType('MCQ');
            setOptions(['', '', '', '']);
            resetQuestionEditorState();
            setIsQuestionModalOpen(true);
            return;
        }

        const payload = question.payload || {};
        setEditingQuestion(question);
        setQuestionType(question.question_type || 'MCQ');
        setOptions(Array.isArray(payload.options) && payload.options.length > 0 ? payload.options : ['', '', '', '']);
        setCorrectAnswer(Array.isArray(payload.correct_answer) ? '' : (payload.correct_answer || ''));
        setCorrectAnswers(Array.isArray(payload.correct_answer) ? payload.correct_answer : []);
        setTaxonomyLevel(question.taxonomy_level || 3);
        setMorphingStrategy(question.morphing_strategy || '');
        setTimeComplexity(question.time_complexity || payload.time_complexity || '');
        setSpaceComplexity(question.space_complexity || payload.space_complexity || '');

        const testCases = Array.isArray(payload.test_cases) ? payload.test_cases : [];
        setCodingTestCases(
            testCases.length > 0
                ? testCases.map((tc, idx) => ({
                    id: Date.now() + idx,
                    input: tc.input || '',
                    output: tc.output || '',
                    visibility: tc.visibility === 'hidden' ? 'hidden' : 'visible',
                }))
                : [{ id: Date.now(), input: '', output: '', visibility: 'visible' }]
        );
        setCodingHints(Array.isArray(payload.hints) ? payload.hints : []);
        setKeywordTags(Array.isArray(payload.keyword_tags) ? payload.keyword_tags : []);
        setForbiddenBuiltins(Array.isArray(payload.forbidden_builtins) ? payload.forbidden_builtins : []);
        setHintInput('');
        setKeywordTagInput('');
        setForbiddenBuiltinInput('');
        setIsQuestionModalOpen(true);
    };

    const handleBack = () => {
        if (activeView === 'questions') {
            setActiveView('sections');
            setSelectedSectionId(null);
        } else if (activeView === 'sections') {
            setActiveView('exams');
            setSelectedExamId(null);
        }
        setSearchTerm('');
    };

    const handleDeleteQuestion = (id) => {
        const deleteQuestion = async () => {
            const adminToken = localStorage.getItem('admin_token');
            if (!adminToken) {
                setQuestionError('Admin session expired. Please log in again.');
                return;
            }

            try {
                setQuestionError('');
                const res = await fetch(`${API_BASE_URL}/admin/exams/questions/${id}`, {
                    method: 'DELETE',
                    headers: {
                        Authorization: `Bearer ${adminToken}`,
                    },
                });

                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(data?.detail || 'Failed to delete question');
                }

                setQuestions((prev) => prev.filter((q) => q.question_id !== id));
            } catch (error) {
                setQuestionError(error.message || 'Unable to delete question.');
            }
        };

        deleteQuestion();
    };

    const handleSaveQuestion = (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const type = formData.get('type');
        const questionText = String(formData.get('text') || '').trim();

        const saveQuestion = async () => {
            const adminToken = localStorage.getItem('admin_token');
            if (!adminToken) {
                setQuestionError('Admin session expired. Please log in again.');
                return;
            }

            let payload = {
                options: [],
                correct_answer: '',
                question_test: questionText,
            };
            if (type === 'MCQ') {
                payload = { options, correct_answer: correctAnswer, question_test: questionText };
            } else if (type === 'MSQ') {
                payload = { options, correct_answer: correctAnswers, question_test: questionText };
            } else {
                payload = { options: [], correct_answer: correctAnswer, question_test: questionText };
            }

            if (type === 'Coding') {
                payload = {
                    ...payload,
                    test_cases: codingTestCases
                        .map((tc) => ({
                            input: String(tc.input || '').trim(),
                            output: String(tc.output || '').trim(),
                            visibility: tc.visibility === 'hidden' ? 'hidden' : 'visible',
                        }))
                        .filter((tc) => tc.input && tc.output),
                    hints: codingHints,
                    keyword_tags: keywordTags,
                    forbidden_builtins: forbiddenBuiltins,
                    time_complexity: String(timeComplexity || '').trim(),
                    space_complexity: String(spaceComplexity || '').trim(),
                };
            }

            try {
                setQuestionError('');

                if (editingQuestion) {
                    const res = await fetch(`${API_BASE_URL}/admin/exams/questions/${editingQuestion.question_id}`, {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            Authorization: `Bearer ${adminToken}`,
                        },
                        body: JSON.stringify({
                            question_text: questionText,
                            question_type: type,
                            taxonomy_level: taxonomyLevel,
                            marks: parseInt(formData.get('points')),
                            morphing_strategy: morphingStrategy || null,
                            time_complexity: type === 'Coding' ? (timeComplexity || null) : null,
                            space_complexity: type === 'Coding' ? (spaceComplexity || null) : null,
                            payload,
                        }),
                    });

                    const data = await res.json().catch(() => ({}));
                    if (!res.ok) {
                        throw new Error(data?.detail || 'Failed to update question');
                    }

                    setQuestions((prev) =>
                        prev.map((q) =>
                            q.question_id === editingQuestion.question_id
                                ? {
                                    ...q,
                                    question_text: questionText,
                                    question_type: type,
                                    taxonomy_level: taxonomyLevel,
                                    marks: parseInt(formData.get('points')),
                                    morphing_strategy: morphingStrategy || null,
                                    time_complexity: type === 'Coding' ? (timeComplexity || null) : null,
                                    space_complexity: type === 'Coding' ? (spaceComplexity || null) : null,
                                    payload,
                                }
                                : q
                        )
                    );
                } else {
                    const res = await fetch(`${API_BASE_URL}/admin/exams/sections/${selectedSectionId}/questions`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            Authorization: `Bearer ${adminToken}`,
                        },
                        body: JSON.stringify({
                            question_text: questionText,
                            question_type: type,
                            taxonomy_level: taxonomyLevel,
                            marks: parseInt(formData.get('points')),
                            morphing_strategy: morphingStrategy || null,
                            time_complexity: type === 'Coding' ? (timeComplexity || null) : null,
                            space_complexity: type === 'Coding' ? (spaceComplexity || null) : null,
                            payload,
                        }),
                    });

                    const data = await res.json().catch(() => ({}));
                    if (!res.ok) {
                        throw new Error(data?.detail || 'Failed to create question');
                    }

                    if (data.question) {
                        setQuestions((prev) => [data.question, ...prev]);
                    }
                }

                setIsQuestionModalOpen(false);
                setEditingQuestion(null);
                setOptions(['', '', '', '']);
                resetQuestionEditorState();
            } catch (error) {
                setQuestionError(error.message || 'Unable to save question.');
            }
        };

        saveQuestion();
    };

    const createSection = async () => {
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            setSectionError('Admin session expired. Please log in again.');
            return;
        }

        const title = newSectionForm.title.trim();
        if (!title) {
            setSectionError('Section name is required.');
            return;
        }

        try {
            setSectionError('');

            const res = await fetch(`${API_BASE_URL}/admin/exams/${selectedExamId}/sections`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${adminToken}`,
                },
                body: JSON.stringify({
                    title,
                    section_type: newSectionForm.section_type.trim() || 'Mixed',
                    status: 'draft',
                }),
            });

            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to create section');
            }

            if (data.section) {
                setSections((prev) => [...prev, data.section]);
            }

            setNewSectionForm({ title: '', section_type: 'Mixed' });
            setIsAddSectionModalOpen(false);
        } catch (error) {
            setSectionError(error.message || 'Unable to create section.');
        }
    };

    const openEditSectionModal = (section) => {
        setEditingSection(section);
        setEditSectionForm({
            title: section.title || '',
            section_type: section.section_type || 'Mixed',
        });
        setSectionError('');
        setIsEditSectionModalOpen(true);
    };

    const updateSection = async () => {
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            setSectionError('Admin session expired. Please log in again.');
            return;
        }

        if (!editingSection?.section_id) {
            setSectionError('No section selected for editing.');
            return;
        }

        const title = editSectionForm.title.trim();
        const sectionType = editSectionForm.section_type.trim();
        if (!title) {
            setSectionError('Section name is required.');
            return;
        }
        if (!sectionType) {
            setSectionError('Section concept is required.');
            return;
        }

        try {
            setSectionError('');

            const res = await fetch(`${API_BASE_URL}/admin/exams/sections/${editingSection.section_id}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${adminToken}`,
                },
                body: JSON.stringify({
                    title,
                    section_type: sectionType,
                }),
            });

            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to update section');
            }

            setSections((prev) =>
                prev.map((section) =>
                    section.section_id === editingSection.section_id
                        ? { ...section, title, section_type: sectionType }
                        : section
                )
            );

            setIsEditSectionModalOpen(false);
            setEditingSection(null);
            setEditSectionForm({ title: '', section_type: 'Mixed' });
        } catch (error) {
            setSectionError(error.message || 'Unable to update section.');
        }
    };

    const handleDeleteSection = async (section) => {
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            setSectionError('Admin session expired. Please log in again.');
            return;
        }

        const confirmed = window.confirm(`Delete section ${section.title}? This permanently removes section-linked questions and records.`);
        if (!confirmed) {
            return;
        }

        try {
            setSectionError('');

            const res = await fetch(`${API_BASE_URL}/admin/exams/sections/${section.section_id}`, {
                method: 'DELETE',
                headers: {
                    Authorization: `Bearer ${adminToken}`,
                },
            });

            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to delete section');
            }

            setSections((prev) => prev.filter((s) => s.section_id !== section.section_id));
            if (selectedSectionId === section.section_id) {
                setSelectedSectionId(null);
                setQuestions([]);
                setActiveView('sections');
            }
        } catch (error) {
            setSectionError(error.message || 'Unable to delete section.');
        }
    };

    return (
        <div className="space-y-6 h-full flex flex-col relative">
            {/* Header */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div className="flex items-center gap-3">
                    {activeView !== 'exams' && (
                        <button onClick={handleBack} className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-400 hover:text-gray-900">
                            <ArrowLeft className="w-5 h-5" />
                        </button>
                    )}
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">
                            {activeView === 'exams' ? 'Section Builder' :
                                activeView === 'sections' ? `${activeExam?.title || ''} Sections` :
                                    `${activeSection?.title || ''} Questions`}
                        </h1>
                        <p className="text-gray-500 font-medium mt-1">
                            {activeView === 'exams' ? 'Select an exam to manage its sections.' :
                                activeView === 'sections' ? 'Manage sections for this exam.' :
                                    'Add and edit questions for this section.'}
                        </p>
                    </div>
                </div>

                <div className="flex gap-2 w-full sm:w-auto">
                    {(activeView === 'sections' || activeView === 'questions') && (
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                            <input type="text" placeholder="Search..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="w-full pl-9 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl focus:ring-1 focus:ring-indigo-500 font-medium text-sm text-gray-900 outline-none" />
                        </div>
                    )}
                    {activeView === 'sections' && (
                        <button onClick={() => setIsAddSectionModalOpen(true)} className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all shadow-sm shrink-0">
                            <Plus className="w-4 h-4" /> New Section
                        </button>
                    )}
                    {activeView === 'questions' && (
                        <button onClick={() => openQuestionEditor()} className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-xl font-bold text-sm hover:bg-indigo-500 transition-all shadow-sm shrink-0">
                            <Plus className="w-4 h-4" /> Add Question
                        </button>
                    )}
                </div>
            </div>

            {/* Content Views */}
            {activeView === 'exams' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {exams.map((exam, i) => {
                        const isJit = exam.generation_mode === 'jit';
                        return (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.05 }}
                                key={exam.exam_id}
                                onClick={() => {
                                    if (!isJit) {
                                        setSelectedExamId(exam.exam_id);
                                        setActiveView('sections');
                                    }
                                }}
                                className={`p-6 rounded-2xl border shadow-sm transition-all group flex flex-col h-full ${
                                    isJit
                                        ? 'bg-gradient-to-br from-purple-50/70 to-white border-purple-200 cursor-not-allowed'
                                        : 'bg-white border-gray-200 hover:shadow-md cursor-pointer'
                                }`}
                            >
                                <div className="flex justify-between items-start mb-4">
                                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${isJit ? 'bg-purple-100 text-purple-600' : 'bg-indigo-50 text-indigo-600'}`}>
                                        {isJit ? <Brain className="w-6 h-6" /> : <LayoutDashboard className="w-6 h-6" />}
                                    </div>
                                    <span className={`text-xs font-bold text-gray-400 transition-colors ${!isJit && 'group-hover:text-indigo-600'}`}>
                                        EX-{exam.exam_id}
                                    </span>
                                </div>
                                <h3 className="text-lg font-bold text-gray-900 mb-1">{exam.title}</h3>
                                {isJit ? (
                                    <div className="mt-auto pt-4 border-t border-purple-100 space-y-2">
                                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-bold">
                                            <Brain className="w-3 h-3" /> Handled by AI
                                        </span>
                                        <p className="text-xs font-medium text-purple-500/80 leading-snug">
                                            Questions for this exam are generated on-the-fly per candidate. Manual sections are not required.
                                        </p>
                                    </div>
                                ) : (
                                    <div className="mt-auto pt-4 flex items-center gap-2 text-sm font-medium text-gray-500">
                                        <Layers className="w-4 h-4 text-gray-400" />
                                        <span>{exam.section_count || 0} Sections</span>
                                    </div>
                                )}
                            </motion.div>
                        );
                    })}
                    {!loadingExams && exams.length === 0 && (
                        <div className="col-span-full py-12 text-center text-gray-500 font-medium">No exams found.</div>
                    )}
                </div>
            ) : activeView === 'sections' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                    {loadingSections ? (
                        <div className="col-span-full py-12 text-center text-gray-500 font-medium">Loading sections...</div>
                    ) : filteredSections.length === 0 ? (
                        <div className="col-span-full py-12 text-center text-gray-500 font-medium">No sections found for this exam.</div>
                    ) : (
                        filteredSections.map((section, i) => (
                            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.05 }} key={section.section_id} onClick={() => { setSelectedSectionId(section.section_id); setActiveView('questions'); }} className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow group relative overflow-hidden flex flex-col h-[200px] cursor-pointer">
                                <div className="absolute top-0 left-0 w-full h-1 bg-indigo-500/80"></div>
                                <div className="flex justify-between items-start mb-3">
                                    <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-indigo-50 text-indigo-600 border border-indigo-100"><Layers className="w-5 h-5" /></div>
                                    <div className="flex items-center gap-2">
                                        <span className="inline-flex items-center px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider bg-gray-100 text-gray-500">SEC-{section.section_id}</span>
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                openEditSectionModal(section);
                                            }}
                                            className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                                            title="Edit section"
                                        >
                                            <Edit2 className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleDeleteSection(section);
                                            }}
                                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                            title="Delete section"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                                <div className="flex-1">
                                    <h3 className="text-lg font-bold text-gray-900 truncate">{section.title}</h3>
                                    <p className="text-sm font-medium text-gray-500 mt-1">{section.section_type}</p>
                                </div>
                                <div className="pt-3 border-t border-gray-100 mt-auto flex items-center justify-between">
                                    <div className="flex items-center gap-1.5 text-sm font-bold text-gray-700">
                                        <FileText className="w-4 h-4 text-gray-400" />{section.question_count || 0} <span className="text-gray-400 font-medium">Questions</span>
                                    </div>
                                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${section.status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-600'}`}>{section.status || 'draft'}</span>
                                </div>
                            </motion.div>
                        ))
                    )}
                </div>
            ) : (
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex-1 overflow-hidden flex flex-col relative">
                    <div className="overflow-x-auto scrollbar-hide">
                        <table className="w-full text-left border-collapse min-w-[600px]">
                            <thead className="bg-gray-50/50 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                <tr>
                                    <th className="p-4 pl-6">ID</th>
                                    <th className="p-4">Question Text</th>
                                    <th className="p-4">Type</th>
                                    <th className="p-4">Points</th>
                                    <th className="p-4 pr-6 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {loadingQuestions ? (
                                    <tr><td colSpan="5" className="p-12 text-center text-gray-500 font-medium">Loading questions...</td></tr>
                                ) : filteredQuestions.length === 0 ? (
                                    <tr><td colSpan="5" className="p-12 text-center text-gray-500 font-medium">No questions in this section.</td></tr>
                                ) : (
                                    <AnimatePresence mode="popLayout">
                                        {filteredQuestions.map((q) => (
                                            <motion.tr layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} key={q.question_id} className="hover:bg-gray-50/50 transition-colors group">
                                                <td className="p-4 pl-6 text-xs font-bold text-gray-400">Q-{q.question_id}</td>
                                                <td className="p-4 font-medium text-sm text-gray-900 max-w-md truncate">{q.question_text}</td>
                                                <td className="p-4 text-sm font-medium text-gray-600">
                                                    <span className="inline-flex items-center px-2 py-1 bg-gray-100 rounded text-xs">{q.question_type}</span>
                                                </td>
                                                <td className="p-4 text-sm font-bold text-gray-700">{q.marks}</td>
                                                <td className="p-4 pr-6 text-right">
                                                    <div className="flex items-center justify-end gap-1 opacity-100 md:opacity-0 group-hover:opacity-100 transition-opacity">
                                                        <button onClick={() => openQuestionEditor(q)} className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"><Edit2 className="w-4 h-4" /></button>
                                                        <button onClick={() => handleDeleteQuestion(q.question_id)} className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"><Trash2 className="w-4 h-4" /></button>
                                                    </div>
                                                </td>
                                            </motion.tr>
                                        ))}
                                    </AnimatePresence>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {dataError && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                    {dataError}
                </div>
            )}

            {questionError && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                    {questionError}
                </div>
            )}

            {/* Modals */}
            <AnimatePresence>
                {isAddSectionModalOpen && (
                    <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                        <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }} className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden" onClick={e => e.stopPropagation()}>
                            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                                <h2 className="text-lg font-bold text-gray-900">Create New Section</h2>
                                <button onClick={() => setIsAddSectionModalOpen(false)} className="text-gray-400 hover:text-gray-900 p-1 rounded-lg hover:bg-gray-100 transition-colors"><X className="w-5 h-5" /></button>
                            </div>
                            <div className="p-6 space-y-5">
                                <div>
                                    <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Section Name</label>
                                    <input
                                        type="text"
                                        value={newSectionForm.title}
                                        onChange={(e) => setNewSectionForm((prev) => ({ ...prev, title: e.target.value }))}
                                        placeholder="e.g. Verbal Reasoning"
                                        className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Section Concept (Mixed, MCQ, etc)</label>
                                    <input
                                        type="text"
                                        value={newSectionForm.section_type}
                                        onChange={(e) => setNewSectionForm((prev) => ({ ...prev, section_type: e.target.value }))}
                                        placeholder="e.g. Mixed"
                                        className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                    />
                                </div>
                                {sectionError && (
                                    <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
                                        {sectionError}
                                    </div>
                                )}
                            </div>
                            <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
                                <button onClick={() => setIsAddSectionModalOpen(false)} className="px-4 py-2 bg-white border border-gray-200 rounded-xl font-bold text-sm text-gray-700 hover:bg-gray-50">Cancel</button>
                                <button onClick={createSection} className="px-6 py-2 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800">Create</button>
                            </div>
                        </motion.div>
                    </div>
                )}

                {isEditSectionModalOpen && (
                    <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                        <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }} className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden" onClick={e => e.stopPropagation()}>
                            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                                <h2 className="text-lg font-bold text-gray-900">Edit Section</h2>
                                <button onClick={() => { setIsEditSectionModalOpen(false); setEditingSection(null); }} className="text-gray-400 hover:text-gray-900 p-1 rounded-lg hover:bg-gray-100 transition-colors"><X className="w-5 h-5" /></button>
                            </div>
                            <div className="p-6 space-y-5">
                                <div>
                                    <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Section Name</label>
                                    <input
                                        type="text"
                                        value={editSectionForm.title}
                                        onChange={(e) => setEditSectionForm((prev) => ({ ...prev, title: e.target.value }))}
                                        placeholder="e.g. Verbal Reasoning"
                                        className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Section Concept</label>
                                    <input
                                        type="text"
                                        value={editSectionForm.section_type}
                                        onChange={(e) => setEditSectionForm((prev) => ({ ...prev, section_type: e.target.value }))}
                                        placeholder="e.g. Mixed"
                                        className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                    />
                                </div>
                                {sectionError && (
                                    <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
                                        {sectionError}
                                    </div>
                                )}
                            </div>
                            <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
                                <button onClick={() => { setIsEditSectionModalOpen(false); setEditingSection(null); }} className="px-4 py-2 bg-white border border-gray-200 rounded-xl font-bold text-sm text-gray-700 hover:bg-gray-50">Cancel</button>
                                <button onClick={updateSection} className="px-6 py-2 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800">Save</button>
                            </div>
                        </motion.div>
                    </div>
                )}

                {isQuestionModalOpen && (
                    <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                        <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }} className="bg-white rounded-2xl shadow-xl w-full max-w-lg flex flex-col max-h-[90vh]" onClick={e => e.stopPropagation()}>
                            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50 shrink-0">
                                <h2 className="text-lg font-bold text-gray-900">{editingQuestion ? 'Edit Question' : 'Add Question'}</h2>
                                <button type="button" onClick={() => { setIsQuestionModalOpen(false); setEditingQuestion(null); resetQuestionEditorState(); }} className="text-gray-400 hover:text-gray-900 p-1 rounded-lg hover:bg-gray-100 transition-colors"><X className="w-5 h-5" /></button>
                            </div>
                            <form onSubmit={handleSaveQuestion} className="flex flex-col flex-1 overflow-hidden">
                                <div className="p-6 space-y-5 overflow-y-auto flex-1 scrollbar-hide">
                                    <div>
                                        <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Question Type</label>
                                        <select name="type" value={questionType} onChange={(e) => { setQuestionType(e.target.value); setCorrectAnswer(''); setCorrectAnswers([]); setMorphingStrategy(''); if (e.target.value !== 'Coding') { setTimeComplexity(''); setSpaceComplexity(''); } }} className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900 bg-white">
                                            <option value="MCQ">Multiple Choice (MCQ)</option>
                                            <option value="MSQ">Multiple Select (MSQ)</option>
                                            <option value="Fill in the Blanks">Fill in the Blanks</option>
                                            <option value="Numeric">Numeric Answer</option>
                                            <option value="Short Answer">Short Answer</option>
                                            <option value="Long Answer">Long Answer</option>
                                            <option value="Coding">Coding</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Question Text</label>
                                        <textarea name="text" defaultValue={editingQuestion?.question_text || ''} required rows={4} placeholder="Enter your question here..." className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900 resize-none"></textarea>
                                    </div>

                                    <div>
                                        <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Morphing Strategy</label>
                                        <select
                                            value={morphingStrategy}
                                            onChange={(e) => setMorphingStrategy(e.target.value)}
                                            className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900 bg-white"
                                        >
                                            <option value="">Select Strategy</option>
                                            {(questionType === 'Coding' ? CODING_MORPHING_STRATEGIES : QUESTION_MORPHING_STRATEGIES).map((strategy) => (
                                                <option key={strategy.value} value={strategy.value}>{strategy.label}</option>
                                            ))}
                                        </select>
                                        <div className="mt-2 space-y-1">
                                            {(questionType === 'Coding' ? CODING_MORPHING_STRATEGIES : QUESTION_MORPHING_STRATEGIES).map((strategy) => (
                                                <div key={strategy.value} className={`flex items-start gap-2 text-xs ${morphingStrategy === strategy.value ? 'text-indigo-700' : 'text-gray-500'}`}>
                                                    <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                                                    <span><span className="font-bold">{strategy.label}:</span> {strategy.description}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {(questionType === 'MCQ' || questionType === 'MSQ') && (
                                        <div>
                                            <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Options</label>
                                            <div className="space-y-3">
                                                {options.map((opt, idx) => (
                                                    <div key={idx} className="flex items-center gap-3">
                                                        <span className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-500 shrink-0">{String.fromCharCode(65 + idx)}</span>
                                                        <input type="text" value={opt} onChange={(e) => {
                                                            const newOpts = [...options];
                                                            newOpts[idx] = e.target.value;
                                                            setOptions(newOpts);
                                                        }} placeholder={`Option ${String.fromCharCode(65 + idx)}`} className="w-full px-4 py-2 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900" required />
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Correct Answer */}
                                    {questionType === 'MCQ' && (
                                        <div>
                                            <label className="block text-xs font-bold text-gray-700 uppercase mb-2">Correct Option</label>
                                            <div className="space-y-2">
                                                {options.map((opt, idx) => {
                                                    const letter = String.fromCharCode(65 + idx);
                                                    return (
                                                        <label key={idx} className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${correctAnswer === letter ? 'bg-indigo-50 border-indigo-300' : 'bg-gray-50 border-gray-200 hover:border-gray-300'}`}>
                                                            <input type="radio" name="correct_option" value={letter} checked={correctAnswer === letter} onChange={() => setCorrectAnswer(letter)} className="accent-indigo-600" />
                                                            <span className="w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center text-xs font-bold text-gray-600 shrink-0">{letter}</span>
                                                            <span className="text-sm font-medium text-gray-700 flex-1">{opt || `Option ${letter}`}</span>
                                                        </label>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}

                                    {questionType === 'MSQ' && (
                                        <div>
                                            <label className="block text-xs font-bold text-gray-700 uppercase mb-2">Correct Options <span className="font-normal normal-case text-gray-400">(select all that apply)</span></label>
                                            <div className="space-y-2">
                                                {options.map((opt, idx) => {
                                                    const letter = String.fromCharCode(65 + idx);
                                                    const isChecked = correctAnswers.includes(letter);
                                                    return (
                                                        <label key={idx} className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${isChecked ? 'bg-indigo-50 border-indigo-300' : 'bg-gray-50 border-gray-200 hover:border-gray-300'}`}>
                                                            <input type="checkbox" checked={isChecked} onChange={() => setCorrectAnswers(prev => isChecked ? prev.filter(a => a !== letter) : [...prev, letter])} className="accent-indigo-600 w-4 h-4" />
                                                            <span className="w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center text-xs font-bold text-gray-600 shrink-0">{letter}</span>
                                                            <span className="text-sm font-medium text-gray-700 flex-1">{opt || `Option ${letter}`}</span>
                                                        </label>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}

                                    {(questionType === 'Fill in the Blanks' || questionType === 'Numeric') && (
                                        <div>
                                            <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Correct Answer</label>
                                            <input
                                                type={questionType === 'Numeric' ? 'number' : 'text'}
                                                value={correctAnswer}
                                                onChange={(e) => setCorrectAnswer(e.target.value)}
                                                placeholder={questionType === 'Numeric' ? 'Enter the numeric answer...' : 'Enter the correct answer...'}
                                                className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                            />
                                        </div>
                                    )}

                                    {(questionType === 'Short Answer' || questionType === 'Long Answer' || questionType === 'Coding') && (
                                        <div>
                                            <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">{questionType === 'Coding' ? 'Model Solution' : 'Model Answer'}</label>
                                            <textarea
                                                rows={questionType === 'Coding' || questionType === 'Long Answer' ? 5 : 3}
                                                value={correctAnswer}
                                                onChange={(e) => setCorrectAnswer(e.target.value)}
                                                placeholder={questionType === 'Coding' ? 'Enter the model code solution...' : 'Enter the model answer...'}
                                                className={`w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900 resize-none${questionType === 'Coding' ? ' font-mono' : ''}`}
                                            ></textarea>
                                        </div>
                                    )}

                                    {questionType === 'Coding' && (
                                        <>
                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Time Complexity</label>
                                                    <input
                                                        type="text"
                                                        value={timeComplexity}
                                                        onChange={(e) => setTimeComplexity(e.target.value)}
                                                        placeholder="e.g. O(n log n)"
                                                        className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Space Complexity</label>
                                                    <input
                                                        type="text"
                                                        value={spaceComplexity}
                                                        onChange={(e) => setSpaceComplexity(e.target.value)}
                                                        placeholder="e.g. O(1)"
                                                        className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                                    />
                                                </div>
                                            </div>

                                            <div className="space-y-3 p-4 rounded-xl border border-gray-200 bg-gray-50/60">
                                                <div className="flex items-center justify-between">
                                                    <label className="block text-xs font-bold text-gray-700 uppercase">Test Cases</label>
                                                    <button type="button" onClick={addCodingTestCase} className="text-xs font-bold text-indigo-600 hover:text-indigo-700">+ Add Test Case</button>
                                                </div>
                                                {codingTestCases.map((tc) => (
                                                    <div key={tc.id} className="grid grid-cols-1 gap-2 rounded-lg border border-gray-200 bg-white p-3">
                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                                            <input
                                                                type="text"
                                                                value={tc.input}
                                                                onChange={(e) => updateCodingTestCase(tc.id, 'input', e.target.value)}
                                                                placeholder="Test input"
                                                                className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                                            />
                                                            <input
                                                                type="text"
                                                                value={tc.output}
                                                                onChange={(e) => updateCodingTestCase(tc.id, 'output', e.target.value)}
                                                                placeholder="Expected output"
                                                                className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900"
                                                            />
                                                        </div>
                                                        <div className="flex items-center justify-between gap-2">
                                                            <select
                                                                value={tc.visibility}
                                                                onChange={(e) => updateCodingTestCase(tc.id, 'visibility', e.target.value)}
                                                                className="px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900 bg-white"
                                                            >
                                                                <option value="visible">Visible Test Case</option>
                                                                <option value="hidden">Hidden Test Case</option>
                                                            </select>
                                                            <button type="button" onClick={() => removeCodingTestCase(tc.id)} className="text-xs font-bold text-red-600 hover:text-red-700">Remove</button>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>

                                            <div>
                                                <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Hints</label>
                                                <div className="flex gap-2">
                                                    <input type="text" value={hintInput} onChange={(e) => setHintInput(e.target.value)} placeholder="e.g. array, unsorted" className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900" />
                                                    <button type="button" onClick={() => { addUniqueListItem(setCodingHints, codingHints, hintInput); setHintInput(''); }} className="px-3 py-2 rounded-xl bg-gray-900 text-white text-xs font-bold">Add</button>
                                                </div>
                                                {codingHints.length > 0 && <div className="mt-2 flex flex-wrap gap-2">{codingHints.map((item, idx) => <button key={`${item}-${idx}`} type="button" onClick={() => removeListItem(setCodingHints, codingHints, item)} className="px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 text-xs font-bold border border-indigo-200">{item}</button>)}</div>}
                                            </div>

                                            <div>
                                                <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Keyword Tags</label>
                                                <div className="flex gap-2">
                                                    <input type="text" value={keywordTagInput} onChange={(e) => setKeywordTagInput(e.target.value)} placeholder="e.g. array, hashing" className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900" />
                                                    <button type="button" onClick={() => { addUniqueListItem(setKeywordTags, keywordTags, keywordTagInput); setKeywordTagInput(''); }} className="px-3 py-2 rounded-xl bg-gray-900 text-white text-xs font-bold">Add</button>
                                                </div>
                                                {keywordTags.length > 0 && <div className="mt-2 flex flex-wrap gap-2">{keywordTags.map((item, idx) => <button key={`${item}-${idx}`} type="button" onClick={() => removeListItem(setKeywordTags, keywordTags, item)} className="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-bold border border-emerald-200">{item}</button>)}</div>}
                                            </div>

                                            <div>
                                                <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Forbidden Builtins</label>
                                                <div className="flex gap-2">
                                                    <input type="text" value={forbiddenBuiltinInput} onChange={(e) => setForbiddenBuiltinInput(e.target.value)} placeholder="e.g. len(), sort()" className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900" />
                                                    <button type="button" onClick={() => { addUniqueListItem(setForbiddenBuiltins, forbiddenBuiltins, forbiddenBuiltinInput); setForbiddenBuiltinInput(''); }} className="px-3 py-2 rounded-xl bg-gray-900 text-white text-xs font-bold">Add</button>
                                                </div>
                                                {forbiddenBuiltins.length > 0 && <div className="mt-2 flex flex-wrap gap-2">{forbiddenBuiltins.map((item, idx) => <button key={`${item}-${idx}`} type="button" onClick={() => removeListItem(setForbiddenBuiltins, forbiddenBuiltins, item)} className="px-2.5 py-1 rounded-full bg-rose-50 text-rose-700 text-xs font-bold border border-rose-200">{item}</button>)}</div>}
                                            </div>
                                        </>
                                    )}

                                    <div>
                                        <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Taxonomy</label>
                                        <select
                                            value={taxonomyLevel}
                                            onChange={(e) => setTaxonomyLevel(Number(e.target.value))}
                                            className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900 bg-white"
                                        >
                                            <option value={1}>1 - Very Easy - Remember</option>
                                            <option value={2}>2 - Easy - Understand</option>
                                            <option value={3}>3 - Medium - Apply</option>
                                            <option value={4}>4 - Hard - Analyze</option>
                                            <option value={5}>5 - Very Hard - Evaluate</option>
                                        </select>
                                    </div>

                                    <div>
                                        <label className="block text-xs font-bold text-gray-700 uppercase mb-1.5">Points</label>
                                        <input type="number" name="points" defaultValue={editingQuestion?.marks || 1} min="1" required className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900" />
                                    </div>
                                </div>
                                <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3 shrink-0">
                                    <button type="button" onClick={() => { setIsQuestionModalOpen(false); setEditingQuestion(null); resetQuestionEditorState(); }} className="px-4 py-2 bg-white border border-gray-200 rounded-xl font-bold text-sm text-gray-700 hover:bg-gray-50">Cancel</button>
                                    <button type="submit" className="px-6 py-2 bg-indigo-600 text-white rounded-xl font-bold text-sm hover:bg-indigo-500">Save Question</button>
                                </div>
                            </form>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
};



// --- View 4: Question Bank ---
const QuestionBank = () => {
    const [activeView, setActiveView] = useState('exams'); // 'exams' | 'questions'
    const [selectedExamId, setSelectedExamId] = useState(null);
    const [selectedQuestions, setSelectedQuestions] = useState([]);

    // Filters
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedType, setSelectedType] = useState('All');
    const [selectedDifficulty, setSelectedDifficulty] = useState('All');
    const [selectedSubject, setSelectedSubject] = useState('All');

    // Modals
    const [isAddToExamModalOpen, setIsAddToExamModalOpen] = useState(false);
    const [isCreateExamModalOpen, setIsCreateExamModalOpen] = useState(false);

    // Mock Data for Question Bank
    const mockExamsData = [
        { id: 'E-401', title: 'Frontend Developer', questionCount: 45, icon: Layout, color: 'text-indigo-600', bg: 'bg-indigo-50' },
        { id: 'E-402', title: 'Data Science', questionCount: 62, icon: Database, color: 'text-emerald-600', bg: 'bg-emerald-50' },
        { id: 'E-403', title: 'Aptitude & Logic', questionCount: 120, icon: Brain, color: 'text-blue-600', bg: 'bg-blue-50' },
        { id: 'E-404', title: 'Backend Architecture', questionCount: 38, icon: Server, color: 'text-amber-600', bg: 'bg-amber-50' },
    ];

    const mockQuestionsData = [
        { id: 'Q-9921', text: 'Explain the concept of closures in JavaScript with an example.', type: 'Descriptive', subject: 'Frontend Tech', difficulty: 'Medium', examId: 'E-401' },
        { id: 'Q-9922', text: 'Which of the following sorting algorithms has the best average-case time complexity?', type: 'MCQ', subject: 'Algorithms', difficulty: 'Easy', examId: 'E-402' },
        { id: 'Q-9923', text: 'Write a React component that fetches data from an API and implements pagination.', type: 'Coding', subject: 'React.js', difficulty: 'Hard', examId: 'E-401' },
        { id: 'Q-9924', text: 'Identify the memory leak in the provided Python snippet.', type: 'Code Review', subject: 'Python', difficulty: 'Hard', examId: 'E-402' },
        { id: 'Q-9925', text: 'If 5 machines take 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?', type: 'MCQ', subject: 'Aptitude', difficulty: 'Easy', examId: 'E-403' },
        { id: 'Q-9926', text: 'Design a RESTful API schema for a library management system.', type: 'Descriptive', subject: 'System Design', difficulty: 'Medium', examId: 'E-404' },
    ];

    const filteredQuestions = mockQuestionsData.filter(q => {
        const matchesExam = q.examId === selectedExamId;
        const matchesSearch = q.text.toLowerCase().includes(searchTerm.toLowerCase()) || q.id.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesType = selectedType === 'All' || q.type === selectedType;
        const matchesDifficulty = selectedDifficulty === 'All' || q.difficulty === selectedDifficulty;
        const matchesSubject = selectedSubject === 'All' || q.subject === selectedSubject;
        return matchesExam && matchesSearch && matchesType && matchesDifficulty && matchesSubject;
    });

    const activeExam = mockExamsData.find(e => e.id === selectedExamId);

    const toggleQuestionSelection = (id) => {
        setSelectedQuestions(prev =>
            prev.includes(id) ? prev.filter(qId => qId !== id) : [...prev, id]
        );
    };

    const toggleAllSelection = () => {
        if (selectedQuestions.length === filteredQuestions.length) {
            setSelectedQuestions([]);
        } else {
            setSelectedQuestions(filteredQuestions.map(q => q.id));
        }
    };

    return (
        <div className="space-y-6 h-full flex flex-col relative">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    {activeView === 'exams' ? (
                        <>
                            <h1 className="text-2xl font-bold text-gray-900">Question Bank</h1>
                            <p className="text-gray-500 font-medium mt-1">Manage questions organized by exam categories.</p>
                        </>
                    ) : (
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => {
                                    setActiveView('exams');
                                    setSelectedExamId(null);
                                    setSelectedQuestions([]);
                                }}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-400 hover:text-gray-900"
                            >
                                <ArrowLeft className="w-5 h-5" />
                            </button>
                            <div>
                                <h1 className="text-2xl font-bold text-gray-900">{activeExam?.title} Questions</h1>
                                <p className="text-gray-500 font-medium mt-1">{filteredQuestions.length} questions available.</p>
                            </div>
                        </div>
                    )}
                </div>
                {activeView === 'questions' && (
                    <div className="flex gap-2 w-full sm:w-auto">
                        <button className="flex items-center gap-2 px-4 py-2.5 bg-white text-gray-700 border border-gray-200 rounded-xl font-bold text-sm hover:bg-gray-50 transition-colors shadow-sm">
                            <UploadCloud className="w-4 h-4" /> Import CSV
                        </button>
                        <button className="hidden sm:flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-sm">
                            <Plus className="w-4 h-4" /> Add Question
                        </button>
                    </div>
                )}
            </div>

            {activeView === 'exams' ? (
                /* --- Exam Cards Grid --- */
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {mockExamsData.map((exam, i) => (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
                            key={exam.id}
                            onClick={() => {
                                setSelectedExamId(exam.id);
                                setActiveView('questions');
                            }}
                            className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all cursor-pointer group flex flex-col h-full"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${exam.bg} ${exam.color}`}>
                                    <exam.icon className="w-6 h-6" />
                                </div>
                                <span className="text-xs font-bold text-gray-400 group-hover:text-indigo-600 transition-colors">{exam.id}</span>
                            </div>
                            <h3 className="text-lg font-bold text-gray-900 mb-1">{exam.title}</h3>
                            <div className="mt-auto pt-4 flex items-center gap-2 text-sm font-medium text-gray-500">
                                <FileText className="w-4 h-4 text-gray-400" />
                                <span>{exam.questionCount} Questions</span>
                            </div>
                        </motion.div>
                    ))}
                </div>
            ) : (
                /* --- Questions List View --- */
                <>
                    {/* Toolbar */}
                    <div className="flex flex-col sm:flex-row gap-3 bg-white p-2 rounded-2xl border border-gray-200 shadow-sm">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                            <input
                                type="text"
                                placeholder="Search questions by text or ID..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="w-full pl-9 pr-4 py-2 bg-gray-50 border-none rounded-xl focus:ring-1 focus:ring-indigo-500 font-medium text-sm text-gray-900 outline-none"
                            />
                        </div>
                        <div className="flex gap-2 overflow-x-auto pb-1 sm:pb-0 scrollbar-hide">
                            <button
                                onClick={() => setSelectedType('All')}
                                className={`flex whitespace-nowrap items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-colors ${selectedType !== 'All' ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' : 'bg-gray-50 text-gray-600 border border-gray-100 hover:bg-gray-100'}`}
                            >
                                {selectedType !== 'All' ? `Type: ${selectedType}` : 'Type: All'}
                                {selectedType !== 'All' && <X className="w-3 h-3 ml-1" />}
                            </button>
                            <button
                                onClick={() => setSelectedDifficulty('All')}
                                className={`flex whitespace-nowrap items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-colors ${selectedDifficulty !== 'All' ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' : 'bg-gray-50 text-gray-600 border border-gray-100 hover:bg-gray-100'}`}
                            >
                                {selectedDifficulty !== 'All' ? `Difficulty: ${selectedDifficulty}` : 'Difficulty: All'}
                                {selectedDifficulty !== 'All' && <X className="w-3 h-3 ml-1" />}
                            </button>
                            <button
                                onClick={() => setSelectedSubject('All')}
                                className={`flex whitespace-nowrap items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-colors ${selectedSubject !== 'All' ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' : 'bg-gray-50 text-gray-600 border border-gray-100 hover:bg-gray-100'}`}
                            >
                                {selectedSubject !== 'All' ? `Subject: ${selectedSubject}` : 'Subject: All'}
                                {selectedSubject !== 'All' && <X className="w-3 h-3 ml-1" />}
                            </button>
                            <button className="flex whitespace-nowrap items-center gap-2 px-4 py-2 bg-gray-50 border border-gray-100 rounded-xl font-medium text-sm hover:bg-indigo-50 transition-colors text-indigo-600">
                                <Filter className="w-4 h-4" /> Filters
                            </button>
                        </div>
                    </div>

                    {/* Questions Table */}
                    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex-1 overflow-hidden flex flex-col relative pb-16">
                        <div className="overflow-x-auto scrollbar-hide overflow-y-auto max-h-[600px]">
                            <table className="w-full text-left border-collapse min-w-[800px]">
                                <thead className="sticky top-0 bg-white z-10 shadow-sm">
                                    <tr className="bg-gray-50/50 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                        <th className="p-4 pl-6 font-bold w-12">
                                            <input
                                                type="checkbox"
                                                checked={selectedQuestions.length === filteredQuestions.length && filteredQuestions.length > 0}
                                                onChange={toggleAllSelection}
                                                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                                            />
                                        </th>
                                        <th className="p-4 font-bold">Question Detail</th>
                                        <th className="p-4 font-bold w-32">Subject</th>
                                        <th className="p-4 font-bold w-28">Type</th>
                                        <th className="p-4 font-bold w-24">Difficulty</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-100">
                                    <AnimatePresence mode="popLayout">
                                        {filteredQuestions.length > 0 ? (
                                            filteredQuestions.map((q) => (
                                                <motion.tr
                                                    layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}
                                                    key={q.id}
                                                    className={`hover:bg-gray-50/50 transition-colors cursor-pointer ${selectedQuestions.includes(q.id) ? 'bg-indigo-50/30' : ''}`}
                                                    onClick={() => toggleQuestionSelection(q.id)}
                                                >
                                                    <td className="p-4 pl-6 text-gray-400">
                                                        <input
                                                            type="checkbox"
                                                            checked={selectedQuestions.includes(q.id)}
                                                            onChange={() => { }} // handled by row click
                                                            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                                                        />
                                                    </td>
                                                    <td className="p-4">
                                                        <div className="flex gap-3">
                                                            <div className="mt-1">
                                                                {q.type === 'Coding' ? <Code className="w-4 h-4 text-indigo-400" /> :
                                                                    q.type === 'Descriptive' ? <AlignLeft className="w-4 h-4 text-emerald-400" /> :
                                                                        <List className="w-4 h-4 text-blue-400" />}
                                                            </div>
                                                            <div>
                                                                <p className="font-medium text-sm text-gray-900 line-clamp-2 leading-relaxed">{q.text}</p>
                                                                <p className="text-[11px] font-bold text-gray-400 mt-1 tracking-wider uppercase">{q.id}</p>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="p-4">
                                                        <span
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                setSelectedSubject(q.subject);
                                                            }}
                                                            className={`inline-flex items-center px-2 py-1 rounded text-xs font-bold border transition-all cursor-pointer hover:scale-105 active:scale-95 ${selectedSubject === q.subject ? 'bg-indigo-600 text-white border-indigo-700 shadow-sm' : 'bg-gray-100 text-gray-700 border-gray-200/60 hover:bg-gray-200'}`}
                                                        >
                                                            {q.subject}
                                                        </span>
                                                    </td>
                                                    <td className="p-4">
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                setSelectedType(q.type);
                                                            }}
                                                            className={`text-sm font-medium px-2 py-1 rounded border transition-all hover:scale-105 active:scale-95 ${selectedType === q.type ? 'bg-indigo-600 text-white border-indigo-700 shadow-sm' : 'bg-gray-100 text-gray-700 border-gray-200/60 hover:bg-gray-200'}`}
                                                        >
                                                            {q.type}
                                                        </button>
                                                    </td>
                                                    <td className="p-4">
                                                        <span
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                setSelectedDifficulty(q.difficulty);
                                                            }}
                                                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border cursor-pointer hover:opacity-80 transition-all ${q.difficulty === 'Easy' ? 'text-emerald-700 bg-emerald-50 border-emerald-200/60' :
                                                                q.difficulty === 'Medium' ? 'text-amber-700 bg-amber-50 border-amber-200/60' : 'text-red-700 bg-red-50 border-red-200/60'} ${selectedDifficulty === q.difficulty ? 'ring-2 ring-indigo-500 ring-offset-1' : ''}`}
                                                        >
                                                            <div className={`w-1.5 h-1.5 rounded-full ${q.difficulty === 'Easy' ? 'bg-emerald-500' :
                                                                q.difficulty === 'Medium' ? 'bg-amber-500' : 'bg-red-500'}`}></div>
                                                            {q.difficulty}
                                                        </span>
                                                    </td>
                                                </motion.tr>
                                            ))
                                        ) : (
                                            <tr>
                                                <td colSpan="5" className="p-20 text-center">
                                                    <div className="flex flex-col items-center justify-center space-y-3">
                                                        <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center border border-gray-100">
                                                            <Search className="w-8 h-8 text-gray-300" />
                                                        </div>
                                                        <h3 className="text-lg font-bold text-gray-900">No questions found</h3>
                                                        <p className="text-gray-500 font-medium max-w-xs mx-auto text-sm">We couldn't find any questions matching your current filters or search query.</p>
                                                        <button
                                                            onClick={() => {
                                                                setSearchTerm('');
                                                                setSelectedType('All');
                                                                setSelectedDifficulty('All');
                                                                setSelectedSubject('All');
                                                            }}
                                                            className="mt-2 text-indigo-600 font-bold text-sm hover:text-indigo-800 transition-colors"
                                                        >
                                                            Clear all filters
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </AnimatePresence>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            )}

            {/* Global Selection Action Bar */}
            <AnimatePresence>
                {selectedQuestions.length > 0 && activeView === 'questions' && (
                    <motion.div
                        initial={{ y: 50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 50, opacity: 0 }}
                        className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-gray-900 text-white px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-6 z-40 w-[90%] max-w-3xl border border-gray-700"
                    >
                        <div className="flex items-center gap-3">
                            <div className="bg-indigo-500 text-white w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm">
                                {selectedQuestions.length}
                            </div>
                            <span className="font-bold text-sm">Questions Selected</span>
                        </div>
                        <div className="h-6 w-px bg-gray-700"></div>
                        <div className="flex items-center gap-3 ml-auto">
                            <button
                                onClick={() => setIsAddToExamModalOpen(true)}
                                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-xl font-bold text-sm transition-colors border border-gray-700"
                            >
                                Add to Existing Exam
                            </button>
                            <button
                                onClick={() => setIsCreateExamModalOpen(true)}
                                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold text-sm transition-colors shadow-sm shadow-indigo-500/30"
                            >
                                Create New Exam
                            </button>
                            <button
                                onClick={() => setSelectedQuestions([])}
                                className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors ml-2"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Modals */}
            <AnimatePresence>
                {isAddToExamModalOpen && (
                    <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
                            className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                                <h2 className="text-lg font-bold text-gray-900">Add to Existing Exam</h2>
                                <button onClick={() => setIsAddToExamModalOpen(false)} className="text-gray-400 hover:text-gray-900 p-1 rounded-lg hover:bg-gray-100 transition-colors">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                            <div className="p-6 space-y-5">
                                <div className="bg-indigo-50 p-3 rounded-xl border border-indigo-100 flex items-center gap-3">
                                    <List className="w-5 h-5 text-indigo-600" />
                                    <p className="text-sm font-bold text-indigo-900">Adding {selectedQuestions.length} selected questions</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Select Exam</label>
                                    <select className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900 bg-white">
                                        <option value="">-- Choose Exam --</option>
                                        <option value="e1">Frontend Engineering 2024</option>
                                        <option value="e2">Cloud Architect Certification</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Section Name (Existing or New)</label>
                                    <input type="text" placeholder="e.g. Advanced Concepts" className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900" />
                                </div>
                            </div>
                            <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
                                <button onClick={() => setIsAddToExamModalOpen(false)} className="px-4 py-2 bg-white border border-gray-200 rounded-xl font-bold text-sm text-gray-700 hover:bg-gray-50 transition-colors">Cancel</button>
                                <button
                                    onClick={() => {
                                        setIsAddToExamModalOpen(false);
                                        setSelectedQuestions([]);
                                    }}
                                    className="px-6 py-2 bg-emerald-600 text-white rounded-xl font-bold text-sm hover:bg-emerald-500 transition-colors"
                                >
                                    Confirm Addition
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}

                {isCreateExamModalOpen && (
                    <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
                            className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                                <h2 className="text-lg font-bold text-gray-900">Create New Exam</h2>
                                <button onClick={() => setIsCreateExamModalOpen(false)} className="text-gray-400 hover:text-gray-900 p-1 rounded-lg hover:bg-gray-100 transition-colors">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                            <div className="p-6 space-y-5">
                                <div className="bg-indigo-50 p-3 rounded-xl border border-indigo-100 flex items-center gap-3">
                                    <FileText className="w-5 h-5 text-indigo-600" />
                                    <p className="text-sm font-bold text-indigo-900">Pre-populating with {selectedQuestions.length} selected questions</p>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Exam Title</label>
                                    <input type="text" placeholder="e.g. Custom Assessment Task" className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900" />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-1.5 ml-1">Exam Type</label>
                                    <select className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:border-indigo-500 font-medium text-sm text-gray-900 bg-white">
                                        <option>Recruitment</option>
                                        <option>Certification</option>
                                        <option>Internal Training</option>
                                    </select>
                                </div>
                            </div>
                            <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
                                <button onClick={() => setIsCreateExamModalOpen(false)} className="px-4 py-2 bg-white border border-gray-200 rounded-xl font-bold text-sm text-gray-700 hover:bg-gray-50 transition-colors">Cancel</button>
                                <button
                                    onClick={() => {
                                        setIsCreateExamModalOpen(false);
                                        setSelectedQuestions([]);
                                    }}
                                    className="px-6 py-2 bg-indigo-600 text-white rounded-xl font-bold text-sm hover:bg-indigo-500 transition-colors"
                                >
                                    Create Exam
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
};

// --- View 5: Candidate Directory ---
const CandidateDirectory = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedGroup, setSelectedGroup] = useState('All');
    const [selectedStatus, setSelectedStatus] = useState('All');
    const [candidates, setCandidates] = useState([]);
    const [loadingCandidates, setLoadingCandidates] = useState(true);
    const [selectedResultIds, setSelectedResultIds] = useState([]);
    const [publishing, setPublishing] = useState(false);

    useEffect(() => {
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            setCandidates([]);
            setLoadingCandidates(false);
            return;
        }

        const loadCandidates = async () => {
            try {
                setLoadingCandidates(true);
                const res = await fetch(`${API_BASE_URL}/admin/exams/results/candidates`, {
                    headers: {
                        Authorization: `Bearer ${adminToken}`,
                    },
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(data?.detail || 'Failed to load candidates');
                }
                setCandidates(data.candidates || []);
            } catch (error) {
                console.error('Failed to load admin candidates:', error);
                setCandidates([]);
            } finally {
                setLoadingCandidates(false);
            }
        };

        loadCandidates();
    }, []);

    const filteredCandidates = candidates.filter((c) => {
        const searchValue = searchTerm.toLowerCase();
        const matchesSearch =
            String(c.candidate_name || '').toLowerCase().includes(searchValue)
            || String(c.candidate_email || '').toLowerCase().includes(searchValue)
            || String(c.candidate_id || '').toLowerCase().includes(searchValue);
        const matchesGroup = selectedGroup === 'All' || c.exam_title === selectedGroup;
        const matchesStatus = selectedStatus === 'All' || c.status === selectedStatus;
        return matchesSearch && matchesGroup && matchesStatus;
    });

    const toggleSelection = (resultId) => {
        if (!resultId) {
            return;
        }
        setSelectedResultIds((prev) => (
            prev.includes(resultId)
                ? prev.filter((id) => id !== resultId)
                : [...prev, resultId]
        ));
    };

    const publishSelected = async () => {
        if (!selectedResultIds.length) {
            return;
        }
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            return;
        }

        try {
            setPublishing(true);
            const res = await fetch(`${API_BASE_URL}/admin/exams/results/publish`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${adminToken}`,
                },
                body: JSON.stringify({ result_ids: selectedResultIds }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to publish results');
            }

            setCandidates((prev) => prev.map((row) => (
                selectedResultIds.includes(row.result_id)
                    ? { ...row, status: 'Published' }
                    : row
            )));
            setSelectedResultIds([]);
        } catch (error) {
            console.error('Failed to publish selected results:', error);
        } finally {
            setPublishing(false);
        }
    };

    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Candidate Directory</h1>
                    <p className="text-gray-500 font-medium mt-1">Manage test takers, invitations, and group assignments.</p>
                </div>
                <div className="flex gap-2 w-full sm:w-auto">
                    <button
                        onClick={publishSelected}
                        disabled={publishing || selectedResultIds.length === 0}
                        className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-sm disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                    >
                        <Mail className="w-4 h-4" /> {publishing ? 'Publishing...' : `Publish (${selectedResultIds.length})`}
                    </button>
                </div>
            </div>

            {/* Toolbar (Search & Filters) */}
            <div className="flex flex-col sm:flex-row gap-3 bg-white p-2 rounded-2xl border border-gray-200 shadow-sm">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search candidates by name, email, or ID..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 bg-gray-50 border-none rounded-xl focus:ring-1 focus:ring-indigo-500 font-medium text-sm text-gray-900 outline-none"
                    />
                </div>
                <div className="flex gap-2 overflow-x-auto pb-1 sm:pb-0 scrollbar-hide">
                    <button
                        onClick={() => setSelectedGroup('All')}
                        className={`flex whitespace-nowrap items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-colors ${selectedGroup !== 'All' ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' : 'bg-gray-50 text-gray-600 border border-gray-100 hover:bg-gray-100'}`}
                    >
                        {selectedGroup !== 'All' ? `Exam: ${selectedGroup}` : 'Group: All'}
                        {selectedGroup !== 'All' && <X className="w-3 h-3 ml-1" />}
                    </button>
                    <button
                        onClick={() => setSelectedStatus('All')}
                        className={`flex whitespace-nowrap items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-colors ${selectedStatus !== 'All' ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' : 'bg-gray-50 text-gray-600 border border-gray-100 hover:bg-gray-100'}`}
                    >
                        {selectedStatus !== 'All' ? `Status: ${selectedStatus}` : 'Status: All'}
                        {selectedStatus !== 'All' && <X className="w-3 h-3 ml-1" />}
                    </button>
                    <button className="flex whitespace-nowrap items-center gap-2 px-4 py-2 bg-gray-50 border border-gray-100 rounded-xl font-medium text-sm hover:bg-indigo-50 transition-colors text-indigo-600">
                        <Filter className="w-4 h-4" /> Filters
                    </button>
                </div>
            </div>

            {/* Candidates Table */}
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex-1 overflow-hidden flex flex-col">
                <div className="overflow-x-auto scrollbar-hide overflow-y-auto max-h-[600px]">
                    <table className="w-full text-left border-collapse min-w-[800px]">
                        <thead className="sticky top-0 bg-white z-10 shadow-sm">
                            <tr className="bg-gray-50/50 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                <th className="p-4 pl-6 font-bold w-12"><input type="checkbox" className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" /></th>
                                <th className="p-4 font-bold">Candidate</th>
                                <th className="p-4 font-bold">Group (Exam)</th>
                                <th className="p-4 font-bold">Status</th>
                                <th className="p-4 font-bold">Added Date</th>
                                <th className="p-4 font-bold w-24">Last Score</th>
                                <th className="p-4 pr-6 text-right font-bold w-20"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            <AnimatePresence mode="popLayout">
                                {loadingCandidates ? (
                                    <tr>
                                        <td colSpan="7" className="p-20 text-center text-gray-500 font-medium">Loading candidates...</td>
                                    </tr>
                                ) : filteredCandidates.length > 0 ? (
                                    filteredCandidates.map((c) => (
                                        <motion.tr
                                            layout
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            exit={{ opacity: 0, scale: 0.95 }}
                                            transition={{ duration: 0.2 }}
                                            key={`${c.exam_id}-${c.candidate_id}`}
                                            className="hover:bg-gray-50/50 transition-colors group cursor-pointer"
                                        >
                                            <td className="p-4 pl-6 text-gray-400">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedResultIds.includes(c.result_id)}
                                                    onChange={() => toggleSelection(c.result_id)}
                                                    disabled={!c.result_id}
                                                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 disabled:opacity-40"
                                                />
                                            </td>
                                            <td className="p-4 flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-full bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold text-sm border border-indigo-100">
                                                    {String(c.candidate_name || 'C').split(' ').map((n) => n[0]).join('').slice(0, 2)}
                                                </div>
                                                <div>
                                                    <p className="font-bold text-sm text-gray-900">{c.candidate_name}</p>
                                                    <p className="text-xs font-medium text-gray-500">{c.candidate_email}</p>
                                                </div>
                                            </td>
                                            <td className="p-4">
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setSelectedGroup(c.exam_title);
                                                    }}
                                                    className={`inline-flex items-center px-2 py-1 rounded text-xs font-bold border transition-all hover:scale-105 active:scale-95 ${selectedGroup === c.exam_title ? 'bg-indigo-600 text-white border-indigo-700 shadow-sm' : 'bg-gray-100 text-gray-700 border-gray-200/60 hover:bg-gray-200'}`}
                                                >
                                                    {c.exam_title}
                                                </button>
                                            </td>
                                            <td className="p-4">
                                                <span
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setSelectedStatus(c.status);
                                                    }}
                                                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border cursor-pointer hover:opacity-80 transition-all ${c.status === 'Completed' ? 'bg-emerald-50 text-emerald-700 border-emerald-200/60' :
                                                        c.status === 'Pending Eval' ? 'bg-amber-50 text-amber-700 border-amber-200/60' :
                                                            c.status === 'Published' ? 'bg-blue-50 text-blue-700 border-blue-200/60' :
                                                            'bg-blue-50 text-blue-700 border-blue-200/60'
                                                        }`}
                                                >
                                                    <div className={`w-1.5 h-1.5 rounded-full ${c.status === 'Completed' ? 'bg-emerald-500' :
                                                        c.status === 'Pending Eval' ? 'bg-amber-500' :
                                                            c.status === 'Published' ? 'bg-blue-500' :
                                                            'bg-blue-500'
                                                        }`}></div>
                                                    {c.status}
                                                </span>
                                            </td>
                                            <td className="p-4 text-sm font-medium text-gray-600">{c.registered_at ? new Date(c.registered_at).toLocaleDateString() : 'N/A'}</td>
                                            <td className="p-4 text-sm font-bold text-gray-900">{c.last_score === null || c.last_score === undefined ? '-' : `${c.last_score}`}</td>
                                            <td className="p-4 pr-6 text-right">
                                                <button className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100">
                                                    <MoreVertical className="w-4 h-4" />
                                                </button>
                                            </td>
                                        </motion.tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan="7" className="p-20 text-center">
                                            <div className="flex flex-col items-center justify-center space-y-3">
                                                <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center border border-gray-100">
                                                    <Search className="w-8 h-8 text-gray-300" />
                                                </div>
                                                <h3 className="text-lg font-bold text-gray-900">No candidates found</h3>
                                                <p className="text-gray-500 font-medium max-w-xs mx-auto text-sm">We couldn't find any candidates matching your current filters or search query.</p>
                                                <button
                                                    onClick={() => {
                                                        setSearchTerm('');
                                                        setSelectedGroup('All');
                                                        setSelectedStatus('All');
                                                    }}
                                                    className="mt-2 text-indigo-600 font-bold text-sm hover:text-indigo-800 transition-colors"
                                                >
                                                    Clear all filters
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                            </AnimatePresence>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

// --- View 6: Live Test Monitoring ---
const LiveMonitoring = () => {
    const mockActiveSessions = [
        { id: 'S-772', candidate: 'Alex Johnson', exam: 'Q3 Software Engineer', timeElapsed: '45m 12s', progress: 68, status: 'Normal', alerts: 0 },
        { id: 'S-771', candidate: 'Michael Chang', exam: 'Q3 Software Engineer', timeElapsed: '42m 05s', progress: 55, status: 'Warning', alerts: 2 },
        { id: 'S-770', candidate: 'Sarah Oconnor', exam: 'AWS Cloud Practitioner', timeElapsed: '1h 15m', progress: 85, status: 'Critical', alerts: 5 },
        { id: 'S-769', candidate: 'David Miller', exam: 'AWS Cloud Practitioner', timeElapsed: '1h 10m', progress: 80, status: 'Normal', alerts: 1 },
    ];

    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                        Live Monitoring
                        <span className="flex h-3 w-3 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                        </span>
                    </h1>
                    <p className="text-gray-500 font-medium mt-1">Real-time proctoring and exam session oversight.</p>
                </div>
                <div className="flex gap-2 w-full sm:w-auto">
                    <button className="flex items-center gap-2 px-4 py-2.5 bg-white text-red-600 border border-red-200 rounded-xl font-bold text-sm hover:bg-red-50 transition-colors shadow-sm">
                        <PauseCircle className="w-4 h-4" /> Pause All
                    </button>
                    <button className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-sm">
                        <Monitor className="w-4 h-4" /> Grid View
                    </button>
                </div>
            </div>

            {/* Live Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                {[
                    { label: 'Active Sessions', value: '1,242', change: '+12 in last 5m', icon: Activity, color: 'blue' },
                    { label: 'System Flags', value: '18', change: 'Requires review', icon: AlertTriangle, color: 'amber' },
                    { label: 'Bandwidth Load', value: '45%', change: 'Stable', icon: Network, color: 'emerald' },
                ].map((stat, i) => (
                    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.1 }} key={i} className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex items-start justify-between">
                        <div>
                            <p className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-1">{stat.label}</p>
                            <h3 className="text-3xl font-black text-gray-900">{stat.value}</h3>
                            <p className={`text-sm font-medium mt-1 ${stat.color === 'amber' ? 'text-amber-600' : 'text-gray-400'}`}>{stat.change}</p>
                        </div>
                        <div className={`p-3 bg-${stat.color}-50 text-${stat.color}-600 justify-center rounded-xl border border-${stat.color}-100`}>
                            <stat.icon className="w-6 h-6" />
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Active Sessions List */}
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex-1 overflow-hidden flex flex-col">
                <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                    <h3 className="font-bold text-gray-900">Current Sessions</h3>
                    <div className="flex gap-2">
                        <button className="text-sm font-bold text-gray-500 hover:text-gray-900 transition-colors">Filter Active</button>
                    </div>
                </div>
                <div className="overflow-x-auto scrollbar-hide">
                    <table className="w-full text-left border-collapse min-w-[900px]">
                        <thead>
                            <tr className="bg-white border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                <th className="p-4 pl-6 font-bold">Candidate</th>
                                <th className="p-4 font-bold">Exam</th>
                                <th className="p-4 font-bold">Time Elapsed</th>
                                <th className="p-4 font-bold w-48">Progress</th>
                                <th className="p-4 font-bold">Proctor Status</th>
                                <th className="p-4 pr-6 text-right font-bold">Intervene</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {mockActiveSessions.map((session, i) => (
                                <motion.tr
                                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                                    key={session.id} className="hover:bg-gray-50/50 transition-colors group"
                                >
                                    <td className="p-4 pl-6 font-bold text-sm text-gray-900 flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold text-xs border border-indigo-100">
                                            {session.candidate.split(' ').map(n => n[0]).join('')}
                                        </div>
                                        {session.candidate}
                                    </td>
                                    <td className="p-4 text-sm font-medium text-gray-600">{session.exam}</td>
                                    <td className="p-4 text-sm font-bold text-gray-900 font-mono tracking-tight">{session.timeElapsed}</td>
                                    <td className="p-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden border border-gray-200">
                                                <div className="bg-indigo-500 h-2 rounded-full" style={{ width: `${session.progress}%` }}></div>
                                            </div>
                                            <span className="text-xs font-bold text-gray-500 w-8">{session.progress}%</span>
                                        </div>
                                    </td>
                                    <td className="p-4">
                                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border ${session.status === 'Normal' ? 'bg-emerald-50 text-emerald-700 border-emerald-200/60' :
                                            session.status === 'Warning' ? 'bg-amber-50 text-amber-700 border-amber-200/60' :
                                                'bg-red-50 text-red-700 border-red-200/60'
                                            }`}>
                                            <div className={`w-1.5 h-1.5 rounded-full ${session.status === 'Normal' ? 'bg-emerald-500' :
                                                session.status === 'Warning' ? 'bg-amber-500 animate-pulse' :
                                                    'bg-red-500 animate-pulse'
                                                }`}></div>
                                            {session.status} {session.alerts > 0 && `(${session.alerts})`}
                                        </span>
                                    </td>
                                    <td className="p-4 pr-6 text-right">
                                        <button className="p-1 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors mr-1 tooltip">
                                            <Eye className="w-4 h-4" />
                                        </button>
                                        <button className="p-1 text-gray-400 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition-colors mr-1">
                                            <AlertTriangle className="w-4 h-4" />
                                        </button>
                                        <button className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                                            <PauseCircle className="w-4 h-4" />
                                        </button>
                                    </td>
                                </motion.tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

// --- View 7: Results & Evaluation ---
const ResultsEval = () => {
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedStatus, setSelectedStatus] = useState('All');
    const [selectedType, setSelectedType] = useState('All');
    const [selectedExam, setSelectedExam] = useState('All');
    const [selectedPublish, setSelectedPublish] = useState('All');

    useEffect(() => {
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            setResults([]);
            setLoading(false);
            return;
        }

        const loadResults = async () => {
            try {
                setLoading(true);
                const res = await fetch(`${API_BASE_URL}/admin/exams/results`, {
                    headers: {
                        Authorization: `Bearer ${adminToken}`,
                    },
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(data?.detail || 'Failed to load results');
                }
                setResults(data.results || []);
            } catch (error) {
                console.error('Failed to load admin results:', error);
                setResults([]);
            } finally {
                setLoading(false);
            }
        };

        loadResults();
    }, []);

    const getReportLink = async (resultId, action) => {
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            return null;
        }
        const res = await fetch(`${API_BASE_URL}/admin/exams/results/${resultId}/report-link?action=${action}`, {
            headers: {
                Authorization: `Bearer ${adminToken}`,
            },
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(data?.detail || 'Unable to fetch report link');
        }
        return data.report_url || null;
    };

    const handlePreview = async (resultId) => {
        try {
            const link = await getReportLink(resultId, 'preview');
            if (!link) {
                return;
            }
            window.open(link, '_blank', 'noopener,noreferrer');
        } catch (error) {
            console.error('Preview failed:', error);
        }
    };

    const handleShare = async (resultId) => {
        try {
            const link = await getReportLink(resultId, 'share');
            if (!link) {
                return;
            }
            window.open(link, '_blank', 'noopener,noreferrer');
        } catch (error) {
            console.error('Share failed:', error);
        }
    };

    const handleDownload = async (resultId) => {
        try {
            const link = await getReportLink(resultId, 'download');
            if (!link) {
                return;
            }
            window.open(link, '_blank', 'noopener,noreferrer');
        } catch (error) {
            console.error('Download failed:', error);
        }
    };

    const examTypes = useMemo(
        () => Array.from(new Set(results.map((row) => String(row.exam_type || '').trim()).filter(Boolean))).sort((a, b) => a.localeCompare(b)),
        [results]
    );

    const examNames = useMemo(
        () => Array.from(new Set(results.map((row) => String(row.exam || '').trim()).filter(Boolean))).sort((a, b) => a.localeCompare(b)),
        [results]
    );

    const rankedResults = useMemo(() => {
        const rowsByExam = new Map();
        results.forEach((row) => {
            const key = row.exam_id ?? row.exam ?? 'unknown_exam';
            if (!rowsByExam.has(key)) {
                rowsByExam.set(key, []);
            }
            rowsByExam.get(key).push(row);
        });

        const computedRankByResultId = new Map();

        rowsByExam.forEach((rows) => {
            const scoredRows = rows
                .filter((row) => row.score !== null && row.score !== undefined && Number.isFinite(Number(row.score)))
                .sort((a, b) => Number(b.score) - Number(a.score));

            let denseRank = 0;
            let previousScore = null;

            scoredRows.forEach((row) => {
                const currentScore = Number(row.score);
                if (previousScore === null || currentScore !== previousScore) {
                    denseRank += 1;
                    previousScore = currentScore;
                }
                computedRankByResultId.set(row.result_id, denseRank);
            });
        });

        return results.map((row) => ({
            ...row,
            computed_rank: computedRankByResultId.get(row.result_id) ?? null,
        }));
    }, [results]);

    const filteredResults = rankedResults.filter((row) => {
        const value = searchTerm.toLowerCase();
        const matchesSearch = String(row.candidate || '').toLowerCase().includes(value)
            || String(row.exam || '').toLowerCase().includes(value)
            || String(row.exam_type || '').toLowerCase().includes(value)
            || String(row.status || '').toLowerCase().includes(value);

        const matchesStatus = selectedStatus === 'All' || row.status === selectedStatus;
        const matchesType = selectedType === 'All' || String(row.exam_type || '') === selectedType;
        const matchesExam = selectedExam === 'All' || String(row.exam || '') === selectedExam;

        const rowPublishLabel = row.published_to_candidate ? 'Published' : 'Unpublished';
        const matchesPublish = selectedPublish === 'All' || rowPublishLabel === selectedPublish;

        return matchesSearch && matchesStatus && matchesType && matchesExam && matchesPublish;
    });

    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Results & Evaluation</h1>
                    <p className="text-gray-500 font-medium mt-1">Review scores, evaluate pending tests, and export data.</p>
                </div>
                <div className="flex gap-2 w-full sm:w-auto">
                    <button className="flex items-center gap-2 px-4 py-2.5 bg-white text-gray-700 border border-gray-200 rounded-xl font-bold text-sm hover:bg-gray-50 transition-colors shadow-sm">
                        <Download className="w-4 h-4" /> Export All
                    </button>
                    <button className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-sm">
                        <CheckSquare className="w-4 h-4" /> Pending Evaluations (1)
                    </button>
                </div>
            </div>

            {/* Toolbar */}
            <div className="flex flex-col sm:flex-row gap-3 bg-white p-2 rounded-2xl border border-gray-200 shadow-sm">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search by candidate name or exam..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 bg-gray-50 border-none rounded-xl focus:ring-1 focus:ring-indigo-500 font-medium text-sm text-gray-900 outline-none"
                    />
                </div>
                <div className="flex gap-2 overflow-x-auto pb-1 sm:pb-0 scrollbar-hide">
                    <button
                        onClick={() => setSelectedStatus('All')}
                        className={`flex whitespace-nowrap items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-colors ${selectedStatus !== 'All' ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' : 'bg-gray-50 text-gray-600 border border-gray-100 hover:bg-gray-100'}`}
                    >
                        {selectedStatus !== 'All' ? `Status: ${selectedStatus}` : 'Status: All'}
                        {selectedStatus !== 'All' && <X className="w-3 h-3 ml-1" />}
                    </button>
                    <button
                        onClick={() => setSelectedType('All')}
                        className={`flex whitespace-nowrap items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-colors ${selectedType !== 'All' ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' : 'bg-gray-50 text-gray-600 border border-gray-100 hover:bg-gray-100'}`}
                    >
                        {selectedType !== 'All' ? `Type: ${selectedType}` : 'Type: All'}
                        {selectedType !== 'All' && <X className="w-3 h-3 ml-1" />}
                    </button>
                    <button
                        onClick={() => setSelectedExam('All')}
                        className={`flex whitespace-nowrap items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-colors ${selectedExam !== 'All' ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' : 'bg-gray-50 text-gray-600 border border-gray-100 hover:bg-gray-100'}`}
                    >
                        {selectedExam !== 'All' ? `Exam: ${selectedExam}` : 'Exam: All'}
                        {selectedExam !== 'All' && <X className="w-3 h-3 ml-1" />}
                    </button>
                    <button
                        onClick={() => setSelectedPublish('All')}
                        className={`flex whitespace-nowrap items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-colors ${selectedPublish !== 'All' ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' : 'bg-gray-50 text-gray-600 border border-gray-100 hover:bg-gray-100'}`}
                    >
                        {selectedPublish !== 'All' ? selectedPublish : 'Published: All'}
                        {selectedPublish !== 'All' && <X className="w-3 h-3 ml-1" />}
                    </button>
                    <button
                        onClick={() => {
                            setSelectedStatus('All');
                            setSelectedType('All');
                            setSelectedExam('All');
                            setSelectedPublish('All');
                            setSearchTerm('');
                        }}
                        className="flex whitespace-nowrap items-center gap-2 px-4 py-2 bg-gray-50 border border-gray-100 rounded-xl font-medium text-sm hover:bg-gray-100 transition-colors"
                    >
                        <Filter className="w-4 h-4" /> Filters
                    </button>
                </div>
            </div>

            <div className="flex flex-wrap gap-2">
                {['Passed', 'Failed', 'Pending Eval'].map((statusLabel) => (
                    <button
                        key={statusLabel}
                        onClick={() => setSelectedStatus(statusLabel)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all hover:scale-105 active:scale-95 ${selectedStatus === statusLabel ? 'bg-indigo-600 text-white border-indigo-700 shadow-sm' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}
                    >
                        {statusLabel}
                    </button>
                ))}
                {['Published', 'Unpublished'].map((publishLabel) => (
                    <button
                        key={publishLabel}
                        onClick={() => setSelectedPublish(publishLabel)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all hover:scale-105 active:scale-95 ${selectedPublish === publishLabel ? 'bg-indigo-600 text-white border-indigo-700 shadow-sm' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}
                    >
                        {publishLabel}
                    </button>
                ))}
                {examTypes.map((examType) => (
                    <button
                        key={examType}
                        onClick={() => setSelectedType(examType)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all hover:scale-105 active:scale-95 ${selectedType === examType ? 'bg-indigo-600 text-white border-indigo-700 shadow-sm' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}
                    >
                        {examType}
                    </button>
                ))}
                {examNames.slice(0, 8).map((examName) => (
                    <button
                        key={examName}
                        onClick={() => setSelectedExam(examName)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all hover:scale-105 active:scale-95 ${selectedExam === examName ? 'bg-indigo-600 text-white border-indigo-700 shadow-sm' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}
                    >
                        {examName}
                    </button>
                ))}
            </div>

            {/* Results Table */}
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex-1 overflow-hidden flex flex-col">
                <div className="overflow-x-auto scrollbar-hide">
                    <table className="w-full text-left border-collapse min-w-[900px]">
                        <thead>
                            <tr className="bg-gray-50/50 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                <th className="p-4 pl-6 font-bold w-12"><input type="checkbox" className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" /></th>
                                <th className="p-4 font-bold">Candidate</th>
                                <th className="p-4 font-bold">Exam</th>
                                <th className="p-4 font-bold">Score</th>
                                <th className="p-4 font-bold">Rank</th>
                                <th className="p-4 font-bold">Status</th>
                                <th className="p-4 font-bold">Date Completed</th>
                                <th className="p-4 pr-6 text-right font-bold w-20">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {loading ? (
                                <tr>
                                    <td colSpan="8" className="p-10 text-center text-gray-500 font-medium">Loading results...</td>
                                </tr>
                            ) : filteredResults.length === 0 ? (
                                <tr>
                                    <td colSpan="8" className="p-10 text-center text-gray-500 font-medium">No result rows found for current filters.</td>
                                </tr>
                            ) : filteredResults.map((r, i) => (
                                <motion.tr
                                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                                    key={r.result_id} className="hover:bg-gray-50/50 transition-colors group cursor-pointer"
                                >
                                    <td className="p-4 pl-6 text-gray-400">
                                        <input type="checkbox" className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                                    </td>
                                    <td className="p-4 flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold text-xs border border-indigo-100">
                                            {r.candidate.split(' ').map(n => n[0]).join('')}
                                        </div>
                                        <p className="font-bold text-sm text-gray-900">{r.candidate}</p>
                                    </td>
                                    <td className="p-4 text-sm font-medium text-gray-600">
                                        <button
                                            onClick={() => setSelectedExam(r.exam || 'All')}
                                            className={`text-left px-2 py-1 rounded border transition-all hover:scale-105 active:scale-95 ${selectedExam === r.exam ? 'bg-indigo-600 text-white border-indigo-700 shadow-sm' : 'bg-gray-100 text-gray-700 border-gray-200/60 hover:bg-gray-200'}`}
                                        >
                                            {r.exam}
                                        </button>
                                        <div className="text-xs text-gray-400 mt-1">{r.exam_type || 'N/A'}</div>
                                    </td>
                                    <td className="p-4">
                                        <span className={`text-sm font-black ${r.status === 'Pending Eval' ? 'text-amber-500' : 'text-gray-900'}`}>{r.score === null || r.score === undefined ? '-' : `${r.score}`}</span>
                                    </td>
                                    <td className="p-4 text-sm font-medium text-gray-500">{r.computed_rank === null || r.computed_rank === undefined ? '-' : r.computed_rank}</td>
                                    <td className="p-4">
                                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border ${r.status === 'Passed' ? 'bg-emerald-50 text-emerald-700 border-emerald-200/60' :
                                            r.status === 'Failed' ? 'bg-red-50 text-red-700 border-red-200/60' :
                                                'bg-amber-50 text-amber-700 border-amber-200/60'
                                            }`}>
                                            <div className={`w-1.5 h-1.5 rounded-full ${r.status === 'Passed' ? 'bg-emerald-500' :
                                                r.status === 'Failed' ? 'bg-red-500' :
                                                    'bg-amber-500 animate-pulse'
                                                }`}></div>
                                            {r.status}
                                        </span>
                                    </td>
                                    <td className="p-4 text-sm font-medium text-gray-600">{r.date_completed ? new Date(r.date_completed).toLocaleDateString() : 'N/A'}</td>
                                    <td className="p-4 pr-6 text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all duration-200">
                                                <button onClick={() => handlePreview(r.result_id)} title="Preview Report" className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-colors">
                                                    <Eye className="w-4 h-4" />
                                                </button>
                                                <button onClick={() => handleShare(r.result_id)} title="Share Report" className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-colors">
                                                    <ArrowUpRight className="w-4 h-4" />
                                                </button>
                                                <button onClick={() => handleDownload(r.result_id)} title="Download Report" className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-colors">
                                                    <Download className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </div>
                                    </td>
                                </motion.tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

// --- View 10: Communications ---
const Communications = () => {
    const [activeIndex, setActiveIndex] = useState(0);

    const templates = [
        { name: 'Exam Invitation', type: 'Automated', icon: Mail, active: true, subject: "You're invited to take the {{exam_name}} assessment", body: "Hi {{candidate_name}},\n\nYou have been invited by {{org_name}} to complete the following assessment:\n\n**{{exam_name}}**\nDuration: {{exam_duration}}\n\nPlease ensure you are in a quiet, well-lit environment. Your webcam and microphone will be required.\n\n[Start Assessment Button]\n\nBest regards,\nThe {{org_name}} Team" },
        { name: 'Result Notification', type: 'Automated', icon: CheckCircle2, active: true, subject: "Your results for {{exam_name}} are ready", body: "Hello {{candidate_name}},\n\nYour assessment results for **{{exam_name}}** have been processed.\n\nScore: {{score}}\nPercentile: {{percentile}}\n\nYou can view the detailed breakdown by logging into your dashboard.\n\n[View Full Report]\n\nBest regards,\nObserve Team" },
        { name: 'Security Audit Alert', type: 'Critical', icon: AlertTriangle, active: true, subject: "SECURITY ALERT: Suspicious login detected", body: "Warning,\n\nA new login was detected from an unrecognized IP address for your admin account.\n\nIP: {{ip_address}}\nLocation: {{location}}\nTime: {{timestamp}}\n\nIf this was not you, please secure your account immediately or contact enterprise support.\n\n[Secure My Account]" },
        { name: 'Monthly Usage Insights', type: 'Campaign', icon: BarChart3, active: true, subject: "Your {{org_name}} usage report for {{month}}", body: "Hi Team,\n\nHere are your platform insights for {{month}}:\n\n- Assessments Delivered: {{total_exams}}\n- Active Proctors: {{active_proctors}}\n- Integrity Score: {{integrity_avg}}%\n\nReview the full analytics suite to see geographic distribution and trend analysis.\n\n[Go to Analytics Dashboard]" },
        { name: 'Proctoring Warning', type: 'Automated', icon: ShieldCheck, active: true, subject: "Important: Proctoring violation detected", body: "Hi {{candidate_name}},\n\nOur AI system has flagged a potential violation during your current assessment: **{{exam_name}}**.\n\nReason: {{violation_reason}}\n\nPlease stay within the frame and ensure no other applications are open. Further violations may result in session termination.\n\nObserve Support" },
        { name: 'Candidate Success Story', type: 'Marketing', icon: Megaphone, active: true, subject: "Success Story: How {{company}} improved hiring quality by 40%", body: "Hi {{admin_name}},\n\nDiscover how leaders are using Observe to scale their technical hiring without compromising on integrity.\n\n{{story_preview_text}}\n\n[Read the Full Case Study]" },
        { name: 'Reminder: 24h Left', type: 'Scheduled', icon: Clock, active: true, subject: "Friendly Reminder: Your assessment window closes in 24 hours", body: "Hi {{candidate_name}},\n\nThis is a friendly reminder that you have 24 hours left to complete the **{{exam_name}}** assessment.\n\nWindow Closes: {{expiry_time}}\n\nDon't miss out on this opportunity!\n\n[Complete Now]" },
    ];

    const currentTemplate = templates[activeIndex];

    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Communications</h1>
                    <p className="text-gray-500 font-medium mt-1">Manage email templates, automated alerts, and announcements.</p>
                </div>
                <div className="flex gap-2 w-full sm:w-auto">
                    <button className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-sm">
                        <Plus className="w-4 h-4" /> New Campaign
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-[650px]">
                {/* Left Col: Template List */}
                <div className="lg:col-span-1 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden flex flex-col">
                    <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
                        <h3 className="font-bold text-gray-900">Email Templates</h3>
                        <span className="text-[10px] font-black bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">{templates.length}</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-2 scrollbar-hide space-y-1">
                        {templates.map((t, i) => (
                            <motion.div
                                key={i}
                                onClick={() => setActiveIndex(i)}
                                whileHover={{ scale: 1.01 }}
                                whileTap={{ scale: 0.98 }}
                                className="p-3 rounded-xl flex items-center gap-3 cursor-pointer relative group transition-colors"
                            >
                                {/* Animated Active Background */}
                                {activeIndex === i && (
                                    <motion.div
                                        layoutId="activeTemplateBg"
                                        className="absolute inset-0 bg-gray-900 rounded-xl shadow-md z-0"
                                        transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                                    />
                                )}

                                <div className={`relative z-10 p-2 rounded-lg transition-colors duration-300 ${activeIndex === i ? 'bg-white/10 text-white' : 'bg-gray-100 text-gray-500 group-hover:bg-gray-200'}`}>
                                    <t.icon className="w-4 h-4" />
                                </div>
                                <div className="relative z-10 flex-1">
                                    <p className={`text-sm font-bold transition-colors duration-300 ${activeIndex === i ? 'text-white' : 'text-gray-900'}`}>{t.name}</p>
                                    <p className={`text-[10px] font-black uppercase tracking-widest transition-colors duration-300 ${activeIndex === i ? 'text-gray-400' : 'text-gray-500'}`}>{t.type}</p>
                                </div>
                                {t.active && (
                                    <div className="relative z-10 w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]"></div>
                                )}
                            </motion.div>
                        ))}
                    </div>
                </div>

                {/* Right Col: Editor */}
                <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-200 shadow-sm flex flex-col p-6">
                    <div className="flex justify-between items-center mb-6">
                        <div>
                            <h3 className="text-lg font-bold text-gray-900">Edit Template: {currentTemplate.name}</h3>
                            <p className="text-sm text-gray-500 font-medium">Configure content and trigger rules for this campaign.</p>
                        </div>
                        <div className="flex gap-2">
                            <button className="flex items-center gap-2 px-4 py-2 bg-white text-gray-700 border border-gray-200 rounded-lg font-bold text-sm hover:bg-gray-50 transition-colors">
                                <Eye className="w-4 h-4" /> Preview
                            </button>
                            <button className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white border border-gray-900 rounded-lg font-bold text-sm hover:bg-gray-800 transition-colors shadow-sm">
                                <Save className="w-4 h-4" /> Save
                            </button>
                        </div>
                    </div>

                    <div className="space-y-5 flex-1 flex flex-col">
                        <div>
                            <label className="block text-xs font-black text-gray-500 uppercase tracking-widest mb-1.5 ml-1">Subject Line</label>
                            <input
                                type="text"
                                key={`subject-${activeIndex}`}
                                defaultValue={currentTemplate.subject}
                                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-gray-900 focus:bg-white outline-none transition-all font-bold text-gray-900"
                            />
                        </div>
                        <div className="flex-1 flex flex-col">
                            <label className="block text-xs font-black text-gray-500 uppercase tracking-widest mb-1.5 ml-1">Email Body</label>
                            <div className="flex-1 border border-gray-200 rounded-2xl overflow-hidden flex flex-col min-h-[450px] shadow-inner bg-gray-50/30">
                                {/* Formatting toolbar */}
                                <div className="bg-white border-b border-gray-200 p-2 flex gap-1">
                                    <button className="p-2 hover:bg-gray-100 rounded-lg text-gray-600 font-serif font-bold transition-colors">B</button>
                                    <button className="p-2 hover:bg-gray-100 rounded-lg text-gray-600 font-serif italic transition-colors">I</button>
                                    <button className="p-2 hover:bg-gray-100 rounded-lg text-gray-600 underline transition-colors">U</button>
                                    <div className="w-[1px] h-6 bg-gray-200 mx-2 self-center"></div>
                                    <button className="px-3 py-1.5 text-xs font-bold text-gray-900 bg-white rounded-lg hover:bg-gray-50 border border-gray-200 shadow-sm transition-all active:scale-95 flex items-center gap-2">
                                        <Plus className="w-3.5 h-3.5" /> Insert Variable
                                    </button>
                                </div>
                                <textarea
                                    key={`body-${activeIndex}`}
                                    className="flex-1 p-6 resize-none outline-none font-medium text-gray-700 leading-relaxed bg-transparent scrollbar-hide"
                                    defaultValue={currentTemplate.body}
                                    placeholder="Enter email content here..."
                                ></textarea>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

// --- View 11: Platform Settings ---
const PlatformSettings = () => {
    const [activeTab, setActiveTab] = useState('general');
    const [generalSettings, setGeneralSettings] = useState({
        organization_name: '',
        support_email: '',
    });
    const [loadingGeneral, setLoadingGeneral] = useState(true);
    const [savingGeneral, setSavingGeneral] = useState(false);
    const [generalMessage, setGeneralMessage] = useState('');
    const [generalError, setGeneralError] = useState('');

    const tabs = [
        { id: 'general', label: 'General', icon: Settings },
        { id: 'security', label: 'Security & Proctoring', icon: ShieldCheck },
        { id: 'compliance', label: 'Compliance (GDPR)', icon: Globe },
        { id: 'api', label: 'API Keys', icon: Code },
        { id: 'sso', label: 'Single Sign-On', icon: Lock },
    ];

    useEffect(() => {
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            setGeneralError('Admin session expired. Please log in again.');
            setLoadingGeneral(false);
            return;
        }

        const loadGeneralSettings = async () => {
            try {
                setLoadingGeneral(true);
                setGeneralError('');

                const res = await fetch(`${API_BASE_URL}/auth/admin/me`, {
                    headers: {
                        Authorization: `Bearer ${adminToken}`,
                    },
                });

                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(data?.detail || 'Failed to load admin settings');
                }

                setGeneralSettings({
                    organization_name: data.organization_name || '',
                    support_email: data.support_email || '',
                });
            } catch (error) {
                setGeneralError(error.message || 'Unable to load general settings.');
            } finally {
                setLoadingGeneral(false);
            }
        };

        loadGeneralSettings();
    }, []);

    const updateGeneralField = (field, value) => {
        setGeneralSettings((prev) => ({ ...prev, [field]: value }));
    };

    const saveGeneralSettings = async () => {
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            setGeneralError('Admin session expired. Please log in again.');
            return;
        }

        const organization_name = generalSettings.organization_name.trim();
        const support_email = generalSettings.support_email.trim().toLowerCase();

        if (!organization_name || !support_email) {
            setGeneralError('Organization name and support email are required.');
            return;
        }

        try {
            setSavingGeneral(true);
            setGeneralError('');
            setGeneralMessage('');

            const res = await fetch(`${API_BASE_URL}/auth/admin/general-settings`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${adminToken}`,
                },
                body: JSON.stringify({ organization_name, support_email }),
            });

            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to update settings');
            }

            setGeneralSettings({
                organization_name: data.organization_name || organization_name,
                support_email: data.support_email || support_email,
            });
            setGeneralMessage('General settings updated successfully.');
        } catch (error) {
            setGeneralError(error.message || 'Unable to update general settings.');
        } finally {
            setSavingGeneral(false);
        }
    };

    return (
        <div className="space-y-6 h-full flex flex-col max-w-5xl mx-auto w-full">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Platform Settings</h1>
                    <p className="text-gray-500 font-medium mt-1">Configure organization details, security rules, and integrations.</p>
                </div>
                <button
                    onClick={activeTab === 'general' ? saveGeneralSettings : undefined}
                    disabled={activeTab === 'general' && (savingGeneral || loadingGeneral)}
                    className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
                >
                    <Save className="w-4 h-4" />
                    <span>{savingGeneral && activeTab === 'general' ? 'Saving...' : 'Save Configurations'}</span>
                </button>
            </div>

            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden flex flex-col md:flex-row flex-1">
                {/* Settings Nav */}
                <div className="w-full md:w-64 bg-gray-50/50 border-r border-gray-200 p-4 space-y-1 shrink-0">
                    {tabs.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => setActiveTab(item.id)}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-colors ${activeTab === item.id ? 'bg-white text-indigo-600 shadow-sm border border-gray-200/60' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'}`}
                        >
                            <item.icon className={`w-4 h-4 ${activeTab === item.id ? 'text-indigo-600' : 'text-gray-400'}`} />
                            {item.label}
                        </button>
                    ))}
                </div>

                {/* Settings Content */}
                <div className="p-8 flex-1 overflow-y-auto w-full scrollbar-hide">

                    {/* General Settings */}
                    {activeTab === 'general' && (
                        <div>
                            <h2 className="text-xl font-bold text-gray-900 mb-6">General Information</h2>
                            {generalError && (
                                <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                                    {generalError}
                                </div>
                            )}
                            {generalMessage && (
                                <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
                                    {generalMessage}
                                </div>
                            )}
                            {loadingGeneral && (
                                <div className="mb-4 rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm font-medium text-gray-600">
                                    Loading organization settings...
                                </div>
                            )}
                            <div className="space-y-6 max-w-2xl">
                                <div>
                                    <label className="block text-sm font-bold text-gray-700 mb-1.5">Organization Name</label>
                                    <input
                                        type="text"
                                        value={generalSettings.organization_name}
                                        onChange={(e) => updateGeneralField('organization_name', e.target.value)}
                                        className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:bg-white outline-none transition-all font-medium text-gray-900"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-700 mb-1.5">Support Email</label>
                                    <input
                                        type="email"
                                        value={generalSettings.support_email}
                                        onChange={(e) => updateGeneralField('support_email', e.target.value)}
                                        className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:bg-white outline-none transition-all font-medium text-gray-900"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-700 mb-1.5">Organization Logo</label>
                                    <div className="flex items-center gap-4">
                                        <div className="w-16 h-16 bg-gray-900 rounded-xl flex items-center justify-center text-white font-black text-xl shadow-sm">A</div>
                                        <div className="flex gap-2">
                                            <button className="px-4 py-2 bg-white text-gray-700 border border-gray-200 rounded-lg text-sm font-bold hover:bg-gray-50 transition-colors">Change</button>
                                            <button className="px-4 py-2 bg-white text-red-600 border border-red-100 rounded-lg text-sm font-bold hover:bg-red-50 transition-colors">Remove</button>
                                        </div>
                                    </div>
                                </div>
                                <hr className="border-gray-100 my-8" />
                                <h2 className="text-xl font-bold text-gray-900 mb-6">White-labeling</h2>
                                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-200">
                                    <div>
                                        <p className="font-bold text-sm text-gray-900">Custom Domain</p>
                                        <p className="text-xs font-medium text-gray-500">Host assessments on `assess.yourdomain.com`</p>
                                    </div>
                                    <div className="w-10 h-6 bg-indigo-600 rounded-full flex items-center p-1 cursor-pointer">
                                        <div className="w-4 h-4 bg-white rounded-full shadow-sm transform translate-x-4"></div>
                                    </div>
                                </div>
                                <div>
                                    <button
                                        onClick={saveGeneralSettings}
                                        disabled={savingGeneral || loadingGeneral}
                                        className="px-5 py-2.5 bg-gray-900 text-white rounded-xl text-sm font-bold hover:bg-gray-800 disabled:opacity-60 disabled:cursor-not-allowed"
                                    >
                                        {savingGeneral ? 'Saving...' : 'Update General Settings'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Security Settings */}
                    {activeTab === 'security' && (
                        <div>
                            <h2 className="text-xl font-bold text-gray-900 mb-6">Security & Proctoring Defaults</h2>
                            <div className="space-y-6 max-w-2xl">
                                <div className="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-200 shadow-sm">
                                    <div>
                                        <p className="font-bold text-sm text-gray-900">Global IP Whitelisting</p>
                                        <p className="text-xs font-medium text-gray-500">Restrict exam access to specific corporate IP addresses.</p>
                                    </div>
                                    <div className="w-10 h-6 bg-gray-200 rounded-full flex items-center p-1 cursor-pointer transition-colors">
                                        <div className="w-4 h-4 bg-white rounded-full shadow-sm transform translate-x-0 transition-transform"></div>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-200 shadow-sm">
                                    <div>
                                        <p className="font-bold text-sm text-gray-900">Strict Browser Lock</p>
                                        <p className="text-xs font-medium text-gray-500">Force full-screen mode and disable copy-paste globally.</p>
                                    </div>
                                    <div className="w-10 h-6 bg-indigo-600 rounded-full flex items-center p-1 cursor-pointer transition-colors">
                                        <div className="w-4 h-4 bg-white rounded-full shadow-sm transform translate-x-4 transition-transform"></div>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-200 shadow-sm">
                                    <div>
                                        <p className="font-bold text-sm text-gray-900">Multi-Face Detection Sensitivity</p>
                                        <p className="text-xs font-medium text-gray-500">Adjust the strictness of the AI proctoring background checks.</p>
                                    </div>
                                    <select className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm font-bold text-gray-700 outline-none hover:border-gray-300 transition-colors">
                                        <option>Low</option>
                                        <option>Medium</option>
                                        <option selected>High</option>
                                        <option>Strict (Immediate Flag)</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Compliance Settings */}
                    {activeTab === 'compliance' && (
                        <div>
                            <h2 className="text-xl font-bold text-gray-900 mb-6">Data Privacy & Compliance</h2>
                            <div className="space-y-6 max-w-2xl">
                                <div>
                                    <label className="block text-sm font-bold text-gray-700 mb-1.5">Candidate Data Retention Period</label>
                                    <select className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:bg-white outline-none transition-all font-medium text-gray-900">
                                        <option>30 Days</option>
                                        <option>90 Days</option>
                                        <option selected>1 Year</option>
                                        <option>Indefinitely</option>
                                    </select>
                                    <p className="text-xs text-gray-500 mt-1.5">Candidate personal data and videos will be hard-deleted after this period.</p>
                                </div>
                                <div className="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-200 shadow-sm">
                                    <div>
                                        <p className="font-bold text-sm text-gray-900">Require Explicit GDPR Consent</p>
                                        <p className="text-xs font-medium text-gray-500">Force candidates to accept the privacy policy before starting any exam.</p>
                                    </div>
                                    <div className="w-10 h-6 bg-indigo-600 rounded-full flex items-center p-1 cursor-pointer transition-colors">
                                        <div className="w-4 h-4 bg-white rounded-full shadow-sm transform translate-x-4 transition-transform"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* API Keys */}
                    {activeTab === 'api' && (
                        <div>
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-xl font-bold text-gray-900">API Keys</h2>
                                <button className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-bold hover:bg-gray-50 shadow-sm">Generate New Key</button>
                            </div>
                            <div className="space-y-4 max-w-2xl">
                                <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="font-bold text-sm text-gray-900">Production API Key</span>
                                        <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-bold">Active</span>
                                    </div>
                                    <div className="flex gap-2">
                                        <input type="password" value="sk_prod_xxxxxxxxxxxxxxxxx" readOnly className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-mono text-gray-600 outline-none select-all" />
                                        <button className="px-3 py-2 bg-white border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"><Copy className="w-4 h-4" /></button>
                                    </div>
                                    <p className="text-xs text-gray-500 mt-2">Created Oct 12, 2023. Last used 2 mins ago.</p>
                                </div>
                                <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl opacity-60">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="font-bold text-sm text-gray-900">Staging API Key</span>
                                        <span className="px-2 py-0.5 bg-gray-200 text-gray-600 rounded text-xs font-bold">Revoked</span>
                                    </div>
                                    <div className="flex gap-2">
                                        <input type="password" value="sk_test_xxxxxxxxxxxxxxxxx" readOnly className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-mono text-gray-500 outline-none" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* SSO */}
                    {activeTab === 'sso' && (
                        <div>
                            <h2 className="text-xl font-bold text-gray-900 mb-6">Single Sign-On (SSO)</h2>
                            <div className="space-y-6 max-w-2xl">
                                <div className="p-6 border border-gray-200 rounded-2xl bg-white shadow-sm flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 bg-gray-50 rounded-xl flex items-center justify-center border border-gray-100">
                                            <ShieldCheck className="w-6 h-6 text-indigo-600" />
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-gray-900">SAML 2.0 / Okta</h3>
                                            <p className="text-sm font-medium text-gray-500">Not configured</p>
                                        </div>
                                    </div>
                                    <button className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-bold hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-sm">Configure</button>
                                </div>
                                <div className="p-6 border border-gray-200 rounded-2xl bg-white shadow-sm flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 bg-gray-50 rounded-xl flex items-center justify-center border border-gray-100">
                                            <Globe className="w-6 h-6 text-blue-500" />
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-gray-900">Google Workspace</h3>
                                            <p className="text-sm font-medium text-gray-500">Currently active for @acmecorp.com</p>
                                        </div>
                                    </div>
                                    <button className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-bold hover:bg-gray-50 transition-colors">Manage</button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

// --- View 12: Audit Logs ---
const AuditLogs = () => {
    const mockLogs = [
        { id: 'AL-1092', user: 'System Admin', action: 'Modified Exam "Q3 Software Engineer"', ip: '192.168.1.105', time: '10 mins ago', status: 'Success' },
        { id: 'AL-1091', user: 'Security Bot', action: 'Flagged Candidate "David M." (Violation 2)', ip: '10.0.0.12', time: '1 hour ago', status: 'Alert' },
        { id: 'AL-1090', user: 'Jane Doe (Manager)', action: 'Downloaded "Results_October.csv"', ip: '172.16.254.1', time: '3 hours ago', status: 'Success' },
        { id: 'AL-1089', user: 'System', action: 'Failed login attempt (Admin)', ip: '185.23.10.4', time: 'Yesterday', status: 'Failed' },
        { id: 'AL-1088', user: 'System Admin', action: 'Updated Platform Settings', ip: '192.168.1.105', time: 'Yesterday', status: 'Success' },
    ];

    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Audit Logs</h1>
                    <p className="text-gray-500 font-medium mt-1">Review system events, access logs, and administrative actions.</p>
                </div>
                <div className="flex gap-2 w-full sm:w-auto">
                    <button className="flex items-center gap-2 px-4 py-2.5 bg-white text-gray-700 border border-gray-200 rounded-xl font-bold text-sm hover:bg-gray-50 transition-colors shadow-sm">
                        <DownloadCloud className="w-4 h-4" /> Export CSV
                    </button>
                    <button className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-sm">
                        <FileArchive className="w-4 h-4" /> Log Retention: 90 Days
                    </button>
                </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 bg-white p-2 rounded-2xl border border-gray-200 shadow-sm">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input type="text" placeholder="Search logs by action, user, or IP..." className="w-full pl-9 pr-4 py-2 bg-gray-50 border-none rounded-xl focus:ring-1 focus:ring-indigo-500 font-medium text-sm text-gray-900 outline-none" />
                </div>
                <div className="flex gap-2 overflow-x-auto pb-1 sm:pb-0 scrollbar-hide">
                    <button className="flex whitespace-nowrap items-center gap-2 px-4 py-2 bg-gray-50 text-gray-600 border border-gray-100 rounded-xl font-medium text-sm hover:bg-gray-100 transition-colors">Date: Last 7 Days</button>
                    <button className="flex whitespace-nowrap items-center gap-2 px-4 py-2 bg-gray-50 border border-gray-100 rounded-xl font-medium text-sm hover:bg-indigo-50 transition-colors text-indigo-600">
                        <Filter className="w-4 h-4" /> Filters
                    </button>
                </div>
            </div>

            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex-1 overflow-hidden flex flex-col">
                <div className="overflow-x-auto scrollbar-hide">
                    <table className="w-full text-left border-collapse min-w-[900px]">
                        <thead>
                            <tr className="bg-gray-50/50 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                <th className="p-4 pl-6 font-bold w-24">Event ID</th>
                                <th className="p-4 font-bold">User / Actor</th>
                                <th className="p-4 font-bold max-w-sm">Action Desc.</th>
                                <th className="p-4 font-bold">IP Address</th>
                                <th className="p-4 font-bold">Time</th>
                                <th className="p-4 pr-6 text-right font-bold">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {mockLogs.map((log) => (
                                <tr key={log.id} className="hover:bg-gray-50/50 transition-colors">
                                    <td className="p-4 pl-6 text-sm font-mono text-gray-500">{log.id}</td>
                                    <td className="p-4 text-sm font-bold text-gray-900">{log.user}</td>
                                    <td className="p-4 text-sm font-medium text-gray-600 max-w-sm truncate">{log.action}</td>
                                    <td className="p-4 text-xs font-mono text-gray-500">{log.ip}</td>
                                    <td className="p-4 text-sm text-gray-500 font-medium">{log.time}</td>
                                    <td className="p-4 pr-6 text-right">
                                        <span className={`inline-flex px-2 py-1 rounded text-xs font-bold border ${log.status === 'Success' ? 'bg-gray-50 text-gray-600 border-gray-200' :
                                            log.status === 'Failed' ? 'bg-red-50 text-red-700 border-red-200' :
                                                'bg-amber-50 text-amber-700 border-amber-200'
                                            }`}>{log.status}</span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

// --- View 13: Integrations ---
const Integrations = () => {
    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Integrations & Webhooks</h1>
                    <p className="text-gray-500 font-medium mt-1">Connect Observe with your ATS, LMS, or other HR tools.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[
                    { name: 'Workday API', desc: 'Sync candidates and assessment results automatically.', active: true, icon: Network },
                    { name: 'Greenhouse', desc: 'Directly send candidate invites from Greenhouse ATS.', active: false, icon: Link2 },
                    { name: 'Slack Bot', desc: 'Receive real-time notifications for proctoring flags.', active: true, icon: Webhook },
                    { name: 'Custom Webhooks', desc: 'Set up endpoints to receive JSON payloads on events.', active: false, icon: Code },
                ].map((integ, i) => (
                    <div key={i} className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm flex flex-col items-start gap-4 hover:border-indigo-300 transition-colors group">
                        <div className="w-12 h-12 rounded-xl bg-gray-50 border border-gray-100 flex items-center justify-center text-gray-600 group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors">
                            <integ.icon className="w-6 h-6" />
                        </div>
                        <div>
                            <div className="flex justify-between items-center w-full mb-1">
                                <h3 className="font-bold text-gray-900 text-lg">{integ.name}</h3>
                                {integ.active ? (
                                    <span className="text-xs font-bold px-2 py-1 bg-emerald-50 text-emerald-700 rounded border border-emerald-200">Connected</span>
                                ) : (
                                    <span className="text-xs font-bold px-2 py-1 bg-gray-100 text-gray-500 rounded border border-gray-200">Inactive</span>
                                )}
                            </div>
                            <p className="text-sm text-gray-500">{integ.desc}</p>
                        </div>
                        <div className="mt-auto w-full pt-4 border-t border-gray-100 flex justify-between items-center">
                            {integ.active ? (
                                <>
                                    <button className="text-sm font-bold text-indigo-600 hover:text-indigo-800">Configure</button>
                                    <button className="text-sm font-bold text-gray-400 hover:text-red-600">Disconnect</button>
                                </>
                            ) : (
                                <button className="w-full py-2 bg-gray-900 text-white rounded-lg text-sm font-bold hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20">Enable Integration</button>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

// --- View 14: Billing & Plans ---
const BillingPlans = () => {
    const [activeTab, setActiveTab] = useState('overview');

    const tabs = [
        { id: 'overview', label: 'Billing Overview', icon: LayoutDashboard },
        { id: 'plans', label: 'Available Plans', icon: Layers },
        { id: 'payment', label: 'Payment Methods', icon: CreditCard },
        { id: 'invoices', label: 'Invoices & History', icon: FileText },
    ];

    return (
        <div className="space-y-6 h-full flex flex-col max-w-5xl mx-auto w-full">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Billing & Plans</h1>
                    <p className="text-gray-500 font-medium mt-1">Manage subscriptions, payment methods, and view billing history.</p>
                </div>
            </div>

            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden flex flex-col md:flex-row flex-1">
                {/* Billing Nav */}
                <div className="w-full md:w-64 bg-gray-50/50 border-r border-gray-200 p-4 space-y-1 shrink-0">
                    {tabs.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => setActiveTab(item.id)}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all duration-300 ${activeTab === item.id ? 'bg-white text-indigo-600 shadow-sm border border-gray-200/60' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'}`}
                        >
                            <item.icon className={`w-4 h-4 ${activeTab === item.id ? 'text-indigo-600' : 'text-gray-400'}`} />
                            {item.label}
                        </button>
                    ))}
                </div>

                {/* Billing Content */}
                <div className="p-8 flex-1 overflow-y-auto w-full scrollbar-hide">

                    {/* Overview Tab */}
                    {activeTab === 'overview' && (
                        <div>
                            <h2 className="text-xl font-bold text-gray-900 mb-6">Subscription Overview</h2>

                            <div className="bg-gradient-to-r from-gray-900 to-indigo-900 p-8 rounded-2xl text-white shadow-lg mb-8 relative overflow-hidden">
                                <div className="relative z-10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
                                    <div>
                                        <p className="text-sm font-medium text-indigo-200 uppercase tracking-wider mb-2">Current Plan</p>
                                        <h3 className="text-4xl font-black mb-2">Enterprise Yearly</h3>
                                        <p className="font-medium text-gray-300 flex items-center gap-2">
                                            <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Active • Renews on Jan 14, 2025
                                        </p>
                                    </div>
                                    <button onClick={() => setActiveTab('plans')} className="px-5 py-2.5 bg-white text-gray-900 rounded-xl font-bold text-sm shadow hover:bg-gray-100 transition-colors">
                                        Upgrade Plan
                                    </button>
                                </div>
                                {/* Decorative elements */}
                                <div className="absolute -right-10 -bottom-10 w-40 h-40 bg-indigo-500 rounded-full blur-3xl opacity-20"></div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 flex flex-col justify-between">
                                    <h3 className="font-bold text-gray-900 mb-4">Usage This Month</h3>
                                    <div className="space-y-6">
                                        <div>
                                            <div className="flex justify-between text-sm font-bold mb-2">
                                                <span className="text-gray-700">Assessments Delivered</span>
                                                <span className="text-gray-900">12,492 / 15,000</span>
                                            </div>
                                            <div className="w-full bg-gray-100 rounded-full h-2.5">
                                                <div className="bg-indigo-600 h-2.5 rounded-full" style={{ width: '83%' }}></div>
                                            </div>
                                            <p className="text-xs font-medium text-amber-600 mt-2">83% approaching limit</p>
                                        </div>
                                        <div>
                                            <div className="flex justify-between text-sm font-bold mb-2">
                                                <span className="text-gray-700">Live API Requests</span>
                                                <span className="text-gray-900">450k / 1M</span>
                                            </div>
                                            <div className="w-full bg-gray-100 rounded-full h-2.5">
                                                <div className="bg-emerald-500 h-2.5 rounded-full" style={{ width: '45%' }}></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 flex flex-col justify-between">
                                    <h3 className="font-bold text-gray-900 mb-4">Quick Links</h3>
                                    <div className="space-y-3">
                                        <button onClick={() => setActiveTab('payment')} className="w-full flex items-center justify-between p-3 rounded-xl border border-gray-100 hover:border-gray-300 hover:bg-gray-50 transition-all group">
                                            <div className="flex items-center gap-3">
                                                <CreditCard className="w-5 h-5 text-gray-400 group-hover:text-indigo-600 transition-colors" />
                                                <span className="font-bold text-sm text-gray-700">Update payment method</span>
                                            </div>
                                            <ChevronRight className="w-4 h-4 text-gray-400" />
                                        </button>
                                        <button onClick={() => setActiveTab('invoices')} className="w-full flex items-center justify-between p-3 rounded-xl border border-gray-100 hover:border-gray-300 hover:bg-gray-50 transition-all group">
                                            <div className="flex items-center gap-3">
                                                <FileText className="w-5 h-5 text-gray-400 group-hover:text-indigo-600 transition-colors" />
                                                <span className="font-bold text-sm text-gray-700">Download last invoice</span>
                                            </div>
                                            <ChevronRight className="w-4 h-4 text-gray-400" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Plans Tab */}
                    {activeTab === 'plans' && (
                        <div>
                            <h2 className="text-xl font-bold text-gray-900 mb-6">Available Plans</h2>
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                {/* Starter */}
                                <div className="border border-gray-200 rounded-2xl p-6 bg-white hover:border-indigo-300 transition-colors flex flex-col h-full shadow-sm">
                                    <h3 className="text-lg font-bold text-gray-900 mb-2">Starter</h3>
                                    <p className="text-sm font-medium text-gray-500 mb-6">Perfect for small teams hiring occasionally.</p>
                                    <div className="mb-6">
                                        <span className="text-4xl font-black text-gray-900">$99</span>
                                        <span className="text-gray-500 font-medium">/mo</span>
                                    </div>
                                    <ul className="space-y-3 mb-8 flex-1">
                                        <li className="flex gap-2 text-sm font-medium text-gray-700"><CheckCircle2 className="w-5 h-5 text-indigo-600 shrink-0" /> Up to 50 assessments/mo</li>
                                        <li className="flex gap-2 text-sm font-medium text-gray-700"><CheckCircle2 className="w-5 h-5 text-indigo-600 shrink-0" /> Basic AI proctoring</li>
                                        <li className="flex gap-2 text-sm font-medium text-gray-700"><CheckCircle2 className="w-5 h-5 text-indigo-600 shrink-0" /> Standard support</li>
                                    </ul>
                                    <button className="w-full py-3 bg-gray-50 text-gray-900 font-bold rounded-xl hover:bg-gray-100 transition-colors border border-gray-200">Downgrade</button>
                                </div>

                                {/* Professional */}
                                <div className="border border-gray-200 rounded-2xl p-6 bg-white hover:border-indigo-300 transition-colors flex flex-col h-full shadow-sm">
                                    <h3 className="text-lg font-bold text-gray-900 mb-2">Professional</h3>
                                    <p className="text-sm font-medium text-gray-500 mb-6">Ideal for growing companies with regular hiring.</p>
                                    <div className="mb-6">
                                        <span className="text-4xl font-black text-gray-900">$299</span>
                                        <span className="text-gray-500 font-medium">/mo</span>
                                    </div>
                                    <ul className="space-y-3 mb-8 flex-1">
                                        <li className="flex gap-2 text-sm font-medium text-gray-700"><CheckCircle2 className="w-5 h-5 text-indigo-600 shrink-0" /> Up to 500 assessments/mo</li>
                                        <li className="flex gap-2 text-sm font-medium text-gray-700"><CheckCircle2 className="w-5 h-5 text-indigo-600 shrink-0" /> Advanced AI proctoring</li>
                                        <li className="flex gap-2 text-sm font-medium text-gray-700"><CheckCircle2 className="w-5 h-5 text-indigo-600 shrink-0" /> Priority support</li>
                                        <li className="flex gap-2 text-sm font-medium text-gray-700"><CheckCircle2 className="w-5 h-5 text-indigo-600 shrink-0" /> ATS integrations</li>
                                    </ul>
                                    <button className="w-full py-3 bg-gray-50 text-gray-900 font-bold rounded-xl hover:bg-gray-100 transition-colors border border-gray-200">Downgrade</button>
                                </div>

                                {/* Enterprise */}
                                <div className="border-2 border-indigo-600 rounded-2xl p-6 bg-indigo-50/10 flex flex-col h-full relative overflow-hidden shadow-md">
                                    <div className="absolute top-0 right-0 bg-indigo-600 text-white text-[10px] font-black uppercase px-3 py-1 rounded-bl-lg">Current Plan</div>
                                    <h3 className="text-lg font-bold text-indigo-900 mb-2">Enterprise</h3>
                                    <p className="text-sm font-medium text-gray-500 mb-6">Advanced security and unlimited scalability.</p>
                                    <div className="mb-6">
                                        <span className="text-4xl font-black text-gray-900">Custom</span>
                                    </div>
                                    <ul className="space-y-3 mb-8 flex-1">
                                        <li className="flex gap-2 text-sm font-medium text-gray-700"><CheckCircle2 className="w-5 h-5 text-indigo-600 shrink-0" /> Custom assessment volume</li>
                                        <li className="flex gap-2 text-sm font-medium text-gray-700"><CheckCircle2 className="w-5 h-5 text-indigo-600 shrink-0" /> Live human proctoring option</li>
                                        <li className="flex gap-2 text-sm font-medium text-gray-700"><CheckCircle2 className="w-5 h-5 text-indigo-600 shrink-0" /> Dedicated account manager</li>
                                        <li className="flex gap-2 text-sm font-medium text-gray-700"><CheckCircle2 className="w-5 h-5 text-indigo-600 shrink-0" /> Custom API & SSO</li>
                                    </ul>
                                    <button className="w-full py-3 bg-indigo-600 text-white font-bold rounded-xl cursor-default opacity-90 border-none shadow-sm">Active Plan</button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Payment Methods */}
                    {activeTab === 'payment' && (
                        <div>
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-xl font-bold text-gray-900">Payment Methods</h2>
                                <button className="px-4 py-2 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-sm flex items-center gap-2">
                                    <Plus className="w-4 h-4" /> Add Method
                                </button>
                            </div>

                            <div className="space-y-4 max-w-2xl">
                                <div className="p-4 border border-indigo-200 bg-indigo-50/30 rounded-2xl flex items-center justify-between relative overflow-hidden">
                                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-600"></div>
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-8 bg-white rounded border border-gray-200 flex items-center justify-center font-black text-blue-800 italic text-sm shadow-sm">VISA</div>
                                        <div>
                                            <p className="font-bold text-gray-900 text-sm">Visa ending in 4242</p>
                                            <p className="text-xs font-medium text-gray-500">Expires 12/2026</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <span className="text-xs font-bold px-2 py-1 bg-indigo-100 text-indigo-700 rounded mr-2">Default</span>
                                        <button className="text-gray-400 hover:text-gray-900 transition-colors"><MoreVertical className="w-5 h-5" /></button>
                                    </div>
                                </div>

                                <div className="p-4 border border-gray-200 bg-white rounded-2xl flex items-center justify-between shadow-sm">
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-8 bg-white rounded border border-gray-200 flex items-center justify-center font-black text-orange-500 italic text-sm shadow-sm">MC</div>
                                        <div>
                                            <p className="font-bold text-gray-900 text-sm">Mastercard ending in 8891</p>
                                            <p className="text-xs font-medium text-gray-500">Expires 08/2025</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button className="text-sm font-bold text-gray-500 hover:text-indigo-600 transition-colors mr-2">Make Default</button>
                                        <button className="text-gray-400 hover:text-gray-900 transition-colors"><MoreVertical className="w-5 h-5" /></button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Invoices */}
                    {activeTab === 'invoices' && (
                        <div>
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-xl font-bold text-gray-900">Billing History</h2>
                                <button className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-bold hover:bg-gray-50 shadow-sm flex items-center gap-2">
                                    <DownloadCloud className="w-4 h-4" /> Download All
                                </button>
                            </div>

                            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
                                <table className="w-full text-left">
                                    <thead className="bg-gray-50 border-b border-gray-200">
                                        <tr>
                                            <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Invoice ID</th>
                                            <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                                            <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Amount</th>
                                            <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                                            <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Receipt</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-100">
                                        {[
                                            { id: 'INV-2024-001', date: 'Jan 14, 2024', amount: '$4,999.00', status: 'Paid' },
                                            { id: 'INV-2023-012', date: 'Jan 14, 2023', amount: '$4,000.00', status: 'Paid' },
                                            { id: 'INV-2022-011', date: 'Jan 14, 2022', amount: '$4,000.00', status: 'Paid' },
                                            { id: 'INV-2021-010', date: 'Jan 14, 2021', amount: '$3,500.00', status: 'Paid' },
                                            { id: 'INV-2020-009', date: 'Jan 14, 2020', amount: '$3,500.00', status: 'Paid' },
                                        ].map((inv, i) => (
                                            <tr key={i} className="hover:bg-gray-50 transition-colors">
                                                <td className="px-6 py-4 font-mono text-sm font-medium text-gray-900">{inv.id}</td>
                                                <td className="px-6 py-4 text-sm font-medium text-gray-600">{inv.date}</td>
                                                <td className="px-6 py-4 text-sm font-bold text-gray-900">{inv.amount}</td>
                                                <td className="px-6 py-4">
                                                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-bold border border-emerald-100">
                                                        <CheckCircle className="w-3 h-3" /> {inv.status}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-right">
                                                    <button className="text-gray-400 hover:text-indigo-600 transition-colors p-2 rounded-lg hover:bg-indigo-50">
                                                        <DownloadCloud className="w-5 h-5" />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

// --- View 15: Team Management ---
const TeamManagement = () => {
    const mockTeam = [
        { id: 1, name: 'System Admin', email: 'admin@observe.app', role: 'Super Admin', status: 'Active', activity: 'Just now' },
        { id: 2, name: 'Jane Doe', email: 'jane@observe.app', role: 'Exam Creator', status: 'Active', activity: '2 hours ago' },
        { id: 3, name: 'David Smith', email: 'david@observe.app', role: 'Proctor', status: 'Offline', activity: '1 day ago' }
    ];

    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Co-workers & Team</h1>
                    <p className="text-gray-500 font-medium mt-1">Manage admin access, exam creators, and proctors.</p>
                </div>
                <button className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-sm">
                    <Plus className="w-4 h-4" /> Add Co-worker
                </button>
            </div>

            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex-1 overflow-hidden flex flex-col">
                <div className="overflow-x-auto scrollbar-hide">
                    <table className="w-full text-left border-collapse min-w-[800px]">
                        <thead>
                            <tr className="bg-gray-50/50 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                <th className="p-4 pl-6 font-bold w-12">#</th>
                                <th className="p-4 font-bold">Colleague</th>
                                <th className="p-4 font-bold">Role</th>
                                <th className="p-4 font-bold">Status</th>
                                <th className="p-4 font-bold">Last Active</th>
                                <th className="p-4 pr-6 text-right font-bold">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {mockTeam.map((user) => (
                                <tr key={user.id} className="hover:bg-gray-50/50 transition-colors">
                                    <td className="p-4 pl-6 text-sm font-medium text-gray-500">{user.id}</td>
                                    <td className="p-4">
                                        <div>
                                            <p className="text-sm font-bold text-gray-900">{user.name}</p>
                                            <p className="text-xs text-gray-500 font-medium">{user.email}</p>
                                        </div>
                                    </td>
                                    <td className="p-4">
                                        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-bold bg-indigo-50 border border-indigo-100 text-indigo-700">
                                            {user.role}
                                        </span>
                                    </td>
                                    <td className="p-4">
                                        <div className="flex items-center gap-2">
                                            <span className={`w-2 h-2 rounded-full ${user.status === 'Active' ? 'bg-emerald-500' : 'bg-gray-400'}`}></span>
                                            <span className="text-sm font-medium text-gray-600">{user.status}</span>
                                        </div>
                                    </td>
                                    <td className="p-4 text-sm font-medium text-gray-500">
                                        {user.activity}
                                    </td>
                                    <td className="p-4 pr-6 text-right">
                                        <div className="flex justify-end gap-2">
                                            <button className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"><Edit2 className="w-4 h-4" /></button>
                                            <button className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"><Trash2 className="w-4 h-4" /></button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

// --- View 16: Analytics & Reports ---
const AnalyticsReports = () => {
    const dataPassFail = [
        { name: 'Software Eng', pass: 400, fail: 240 },
        { name: 'Data Sci', pass: 300, fail: 139 },
        { name: 'Product', pass: 200, fail: 98 },
        { name: 'Design', pass: 278, fail: 39 },
        { name: 'Marketing', pass: 189, fail: 48 },
    ];

    const dataActivity = [
        { name: 'Mon', exams: 40 },
        { name: 'Tue', exams: 30 },
        { name: 'Wed', exams: 20 },
        { name: 'Thu', exams: 27 },
        { name: 'Fri', exams: 18 },
        { name: 'Sat', exams: 23 },
        { name: 'Sun', exams: 34 },
    ];

    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Analytics & Reports</h1>
                    <p className="text-gray-500 font-medium mt-1">Deep dive into candidate performance and exam health.</p>
                </div>
                <button className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-sm">
                    <Download className="w-4 h-4" /> Export Report
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Chart 1 */}
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm min-h-[350px] flex flex-col">
                    <h3 className="text-lg font-bold text-gray-900 mb-6">Pass/Fail by Department</h3>
                    <div className="flex-1">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={dataPassFail} margin={{ top: 10, right: 10, left: -25, bottom: 0 }} barSize={20}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6b7280' }} dy={10} />
                                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6b7280' }} />
                                <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }} cursor={{ fill: '#f3f4f6' }} />
                                <Legend wrapperStyle={{ paddingTop: '20px', fontSize: '12px', fontWeight: '600' }} />
                                <Bar dataKey="pass" name="Passed" fill="#10b981" radius={[4, 4, 0, 0]} />
                                <Bar dataKey="fail" name="Failed" fill="#ef4444" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>

                {/* Chart 2 */}
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm min-h-[350px] flex flex-col">
                    <h3 className="text-lg font-bold text-gray-900 mb-6">Weekly Exam Volume</h3>
                    <div className="flex-1">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={dataActivity} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="colorExams" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6b7280' }} dy={10} />
                                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6b7280' }} />
                                <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }} />
                                <Area type="monotone" dataKey="exams" name="Completed Exams" stroke="#7c3aed" strokeWidth={3} fillOpacity={1} fill="url(#colorExams)" activeDot={{ r: 6, strokeWidth: 0, fill: '#7c3aed' }} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>
            </div>
            
            {/* Recent Reports Table */}
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden flex-1 flex flex-col mt-6">
                <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
                    <h3 className="text-sm font-bold text-gray-900">Generated Reports</h3>
                    <button className="text-xs font-bold text-indigo-600 hover:text-indigo-800">View All</button>
                </div>
                <div className="overflow-x-auto scrollbar-hide py-2">
                    {[
                        { title: "Q3 Engineering Assessment Summary", date: "Oct 12, 2025", author: "System Admin" },
                        { title: "Monthly Usage & Billing Metrics", date: "Oct 01, 2025", author: "Jane Doe" },
                        { title: "Suspicious Activity Report - Physics Grp B", date: "Sep 28, 2025", author: "AI Monitor" },
                    ].map((report, i) => (
                         <div key={i} className="px-6 py-4 border-b border-gray-50 hover:bg-gray-50/50 transition-colors flex items-center justify-between group">
                             <div className="flex items-center gap-4">
                                 <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg"><FileText className="w-5 h-5" /></div>
                                 <div>
                                     <h4 className="text-sm font-bold text-gray-900 group-hover:text-indigo-600 transition-colors">{report.title}</h4>
                                     <p className="text-xs font-medium text-gray-500 mt-0.5">Generated by {report.author} • {report.date}</p>
                                 </div>
                             </div>
                             <div className="flex gap-2">
                                <button className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"><Eye className="w-4 h-4"/></button>
                                <button className="p-2 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"><Download className="w-4 h-4"/></button>
                             </div>
                         </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

// --- Main Layout ---
const AdminDashboard = () => {
    const navigate = useNavigate();
    const [activeView, setActiveView] = useState('overview');
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [notifications, setNotifications] = useState([]);

    // Header Dropdown States
    const [isSearchOpen, setIsSearchOpen] = useState(false);
    const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
    const [isQuickActionOpen, setIsQuickActionOpen] = useState(false);

    const headerRef = useRef(null);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (headerRef.current && !headerRef.current.contains(event.target)) {
                setIsSearchOpen(false);
                setIsNotificationsOpen(false);
                setIsQuickActionOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    useEffect(() => {
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            navigate('/admin/login');
            return;
        }

        const loadNotifications = async () => {
            try {
                const res = await fetch(`${API_BASE_URL}/auth/notifications/me`, {
                    headers: {
                        Authorization: `Bearer ${adminToken}`,
                    },
                });

                if (!res.ok) {
                    return;
                }

                const data = await res.json();
                setNotifications(data.notifications || []);
            } catch (error) {
                console.error('Failed to fetch admin notifications:', error);
            }
        };

        loadNotifications();
    }, [navigate]);

    const unreadCount = notifications.filter((item) => !item.is_read).length;

    const formatNotificationTime = (value) => {
        if (!value) {
            return 'Just now';
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return 'Just now';
        }
        return date.toLocaleString();
    };

    const markAllRead = async () => {
        const adminToken = localStorage.getItem('admin_token');
        if (!adminToken) {
            return;
        }

        const unread = notifications.filter((item) => !item.is_read);
        if (!unread.length) {
            return;
        }

        try {
            await Promise.all(
                unread.map((item) =>
                    fetch(`${API_BASE_URL}/auth/notifications/${item.notification_id}/read`, {
                        method: 'PATCH',
                        headers: {
                            Authorization: `Bearer ${adminToken}`,
                        },
                    })
                )
            );

            setNotifications((prev) => prev.map((item) => ({ ...item, is_read: true })));
        } catch (error) {
            console.error('Failed to mark admin notifications as read:', error);
        }
    };

    const toggleDropdown = (setter) => {
        setIsSearchOpen(false);
        setIsNotificationsOpen(false);
        setIsQuickActionOpen(false);
        setter(true);
    };

    const navGroups = [
        {
            label: "Analytics",
            items: [
                { id: 'overview', label: 'Organization Dash', icon: LayoutDashboard },
                { id: 'reports', label: 'Analytics & Reports', icon: BarChart3 }
            ]
        },
        {
            label: "Management",
            items: [
                { id: 'exams', label: 'Exam Management', icon: FileText },
                { id: 'sections', label: 'Section Builder', icon: Database },
                { id: 'questions', label: 'Question Bank', icon: FileSpreadsheet },
            ]
        },
        {
            label: "Operations",
            items: [
                { id: 'candidates', label: 'Candidate Directory', icon: Users },
                { id: 'monitoring', label: 'Live Monitoring', icon: Activity },
                { id: 'results', label: 'Results & Eval', icon: Award },
            ]
        },
        {
            label: "System",
            items: [
                { id: 'team', label: 'Team Management', icon: Users },
                { id: 'communications', label: 'Communications', icon: Send },
                { id: 'billing', label: 'Billing & Plans', icon: CreditCard },
                { id: 'integrations', label: 'Integrations', icon: Network },
                { id: 'audit', label: 'Audit Logs', icon: ShieldCheck },
                { id: 'settings', label: 'Platform Settings', icon: Settings },
            ]
        }
    ];

    const renderView = () => {
        if (activeView === 'overview') return <Overview />;
        if (activeView === 'exams') return <ExamManagement />;
        if (activeView === 'sections') return <SectionManagement />;
        if (activeView === 'questions') return <QuestionBank />;
        if (activeView === 'candidates') return <CandidateDirectory />;
        if (activeView === 'monitoring') return <LiveMonitoring />;
        if (activeView === 'results') return <ResultsEval />;
        if (activeView === 'reports') return <AnalyticsReports />;
        if (activeView === 'communications') return <Communications />;
        if (activeView === 'settings') return <PlatformSettings />;
        if (activeView === 'audit') return <AuditLogs />;
        if (activeView === 'integrations') return <Integrations />;
        if (activeView === 'billing') return <BillingPlans />;
        if (activeView === 'team') return <TeamManagement />;

        const activeItem = navGroups.flatMap(g => g.items).find(i => i.id === activeView);
        if (activeItem) {
            return <PlaceholderView title={activeItem.label} icon={activeItem.icon} />;
        }
        return <PlaceholderView title="View Not Found" icon={ShieldCheck} />;
    };

    return (
        <div className="min-h-screen bg-[#F8FAFC] flex flex-col md:flex-row overflow-hidden font-sans">

            {/* --- Mobile Header --- */}
            <div className="md:hidden bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between sticky top-0 z-50">
                <div className="flex items-center gap-3">
                    <img src="/logo.svg" alt="Observe Logo" className="h-6" />
                </div>
                <button onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)} className="p-2 -mr-2 text-gray-600 hover:text-black hover:bg-gray-50 rounded-lg transition-colors">
                    <Menu className="w-6 h-6" />
                </button>
            </div>

            {/* --- Sidebar Navigation --- */}
            <motion.aside
                className={`
                    fixed md:static inset-y-0 left-0 z-40 w-72 bg-white border-r border-gray-200 flex flex-col h-[100dvh] transition-transform duration-300 ease-in-out
                    ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
                `}
            >
                {/* Brand Header */}
                <div className="p-6 lg:p-8 items-center gap-3 border-b border-gray-100 hidden md:flex shrink-0">
                    <img src="/logo.svg" alt="Observe Logo" className="h-16" />
                </div>

                {/* Nav Links */}
                <div className="flex-1 overflow-y-auto py-6 px-4 space-y-8 scrollbar-hide">
                    {navGroups.map((group, gIdx) => (
                        <div key={gIdx} className="space-y-1">
                            <h4 className="px-4 text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">{group.label}</h4>
                            {group.items.map((item) => (
                                <button
                                    key={item.id}
                                    onClick={() => { setActiveView(item.id); setIsMobileMenuOpen(false); }}
                                    className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-all group relative overflow-hidden ${activeView === item.id ? 'bg-indigo-50 text-indigo-700 font-medium' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900 font-medium'}`}
                                >
                                    {activeView === item.id && (
                                        <motion.div layoutId="activeNavAdmin" className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-500 rounded-r-full" />
                                    )}
                                    <item.icon className={`w-4 h-4 shrink-0 transition-colors ${activeView === item.id ? 'text-indigo-600' : 'text-gray-400 group-hover:text-gray-600'}`} />
                                    <span className="truncate">{item.label}</span>
                                    {activeView !== item.id && (
                                        <ChevronRight className="w-3.5 h-3.5 ml-auto opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all text-gray-300" />
                                    )}
                                </button>
                            ))}
                        </div>
                    ))}
                </div>

                {/* Footer Actions */}
                <div className="p-4 border-t border-gray-100 shrink-0">
                    <button
                        onClick={() => navigate('/admin/login')}
                        className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
                    >
                        <LogOut className="w-4 h-4" /> End Session
                    </button>
                </div>
            </motion.aside>

            {/* --- Main Content Area --- */}
            <main className="flex-1 h-[100dvh] overflow-y-auto relative bg-[#F8FAFC] scrollbar-hide">
                {/* Header Context Bar */}
                <header ref={headerRef} className="sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-gray-200 px-6 md:px-10 py-4 flex items-center justify-between shadow-sm">
                    {/* Left: Admin Identity */}
                    <div className="flex items-center gap-3 w-1/4">
                        <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center border border-indigo-200">
                            <ShieldCheck className="w-4 h-4 text-indigo-600" />
                        </div>
                        <div className="hidden sm:block">
                            <h2 className="text-sm font-bold text-gray-900 leading-tight">System Admin</h2>
                            <p className="text-xs font-medium text-gray-500 leading-tight">Global Access</p>
                        </div>
                    </div>

                    {/* Center: Global Search */}
                    <div className="flex-1 max-w-xl hidden md:block relative">
                        <div 
                            className="relative group cursor-text"
                            onClick={() => toggleDropdown(setIsSearchOpen)}
                        >
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 group-focus-within:text-indigo-500 transition-colors" />
                            <div className="w-full pl-10 pr-4 py-2 bg-gray-100 border border-transparent rounded-xl flex items-center justify-between transition-all font-medium text-sm text-gray-400 shadow-inner group-hover:bg-gray-200/50">
                                <span>Press Ctrl+K to search candidates, exams...</span>
                                <div className="flex gap-1">
                                    <kbd className="hidden lg:inline-flex items-center justify-center px-1.5 py-0.5 border border-gray-300 rounded text-xs font-mono font-bold text-gray-500 bg-white shadow-sm">Ctrl</kbd>
                                    <kbd className="hidden lg:inline-flex items-center justify-center px-1.5 py-0.5 border border-gray-300 rounded text-xs font-mono font-bold text-gray-500 bg-white shadow-sm">K</kbd>
                                </div>
                            </div>
                        </div>

                        {/* Search Dropdown Modal */}
                        <AnimatePresence>
                            {isSearchOpen && (
                                <motion.div 
                                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}
                                    className="absolute top-full left-0 right-0 mt-2 bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden z-50 origin-top"
                                >
                                    <div className="p-3 border-b border-gray-100 flex items-center gap-3 bg-gray-50/50">
                                        <Search className="w-5 h-5 text-indigo-500 shrink-0" />
                                        <input autoFocus type="text" placeholder="Start typing to search..." className="w-full bg-transparent border-none outline-none font-medium text-gray-900 placeholder:text-gray-400" />
                                        <button onClick={() => setIsSearchOpen(false)} className="p-1 rounded bg-gray-200 text-gray-500 hover:bg-red-100 hover:text-red-500 transition-colors text-xs font-bold uppercase">Esc</button>
                                    </div>
                                    <div className="max-h-[300px] overflow-y-auto scrollbar-hide py-2">
                                        <div className="px-4 py-2 text-xs font-bold text-gray-400 uppercase tracking-wider">Recent Searches</div>
                                        {['David Candidate', 'Software Engineer Exam 2025', 'Organization Settings'].map((item, i) => (
                                            <div key={i} className="px-4 py-2.5 hover:bg-indigo-50 cursor-pointer flex items-center gap-3 text-sm text-gray-700 font-medium group transition-colors">
                                                <History className="w-4 h-4 text-gray-400 group-hover:text-indigo-500" />
                                                <span className="group-hover:text-indigo-900">{item}</span>
                                            </div>
                                        ))}
                                        <div className="h-px bg-gray-100 my-2"></div>
                                        <div className="px-4 py-2 text-xs font-bold text-gray-400 uppercase tracking-wider">Quick Actions</div>
                                        <div className="px-4 py-2.5 hover:bg-indigo-50 cursor-pointer flex items-center gap-3 text-sm text-gray-700 font-medium group transition-colors">
                                            <Plus className="w-4 h-4 text-gray-400 group-hover:text-indigo-500" />
                                            <span>Create New Exam</span>
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* Right: Quick Actions & Alerts */}
                    <div className="flex items-center justify-end gap-3 w-1/4 relative">
                        {/* Notifications */}
                        <button 
                            onClick={() => isNotificationsOpen ? setIsNotificationsOpen(false) : toggleDropdown(setIsNotificationsOpen)}
                            className="hidden sm:flex relative p-2 text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-colors"
                        >
                            <Bell className="w-5 h-5" />
                            {unreadCount > 0 && <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-white"></span>}
                        </button>

                        <AnimatePresence>
                            {isNotificationsOpen && (
                                <motion.div 
                                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}
                                    className="absolute top-[calc(100%+12px)] right-16 w-80 bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden z-50 origin-top-right"
                                >
                                    <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                                        <h3 className="font-bold text-gray-900">Notifications</h3>
                                        <button onClick={markAllRead} className="text-xs font-bold text-indigo-600 hover:text-indigo-800">Mark all read</button>
                                    </div>
                                    <div className="max-h-[350px] overflow-y-auto scrollbar-hide">
                                        {notifications.length === 0 && (
                                            <div className="p-4 text-sm text-gray-500">No notifications available.</div>
                                        )}
                                        {notifications.map((n) => (
                                            <div key={n.notification_id} className={`p-4 border-b border-gray-50 hover:bg-gray-50 transition-colors cursor-pointer flex gap-3 ${!n.is_read ? 'bg-indigo-50/20' : ''}`}>
                                                <div className={`w-2 h-2 mt-1.5 rounded-full shrink-0 ${n.is_read ? 'bg-gray-300' : 'bg-indigo-500'}`}></div>
                                                <div>
                                                    <h4 className="text-sm font-bold text-gray-900">{n.title}</h4>
                                                    <p className="text-xs font-medium text-gray-500 mt-0.5">{n.body}</p>
                                                    <span className="text-[10px] font-bold text-gray-400 mt-2 block">{formatNotificationTime(n.created_at)}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                    <button className="w-full p-3 text-center text-xs font-bold text-gray-500 hover:text-gray-900 transition-colors bg-gray-50/50">View All Notifications</button>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Quick Actions */}
                        <div className="relative">
                            <button 
                                onClick={() => isQuickActionOpen ? setIsQuickActionOpen(false) : toggleDropdown(setIsQuickActionOpen)}
                                className="flex items-center gap-2 px-3 py-2 sm:px-4 sm:py-2.5 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-all duration-300 shadow-sm focus:ring-4 focus:ring-indigo-100"
                            >
                                <Plus className="w-4 h-4" />
                                <span className="hidden sm:inline">Quick Action</span>
                            </button>

                            <AnimatePresence>
                                {isQuickActionOpen && (
                                    <motion.div 
                                        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}
                                        className="absolute top-[calc(100%+8px)] right-0 w-56 bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden z-50 origin-top-right py-2"
                                    >
                                        <button onClick={() => { setIsQuickActionOpen(false); setActiveView('exams'); }} className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:text-indigo-600 transition-colors">
                                            <FileText className="w-4 h-4 text-gray-400" /> Create New Exam
                                        </button>
                                        <button onClick={() => { setIsQuickActionOpen(false); setActiveView('candidates'); }} className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:text-indigo-600 transition-colors">
                                            <Users className="w-4 h-4 text-gray-400" /> Invite Candidate
                                        </button>
                                        <button onClick={() => { setIsQuickActionOpen(false); setActiveView('reports'); }} className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:text-indigo-600 transition-colors">
                                            <BarChart3 className="w-4 h-4 text-gray-400" /> Generate Report
                                        </button>
                                        <div className="h-px bg-gray-100 my-1"></div>
                                        <button onClick={() => { setIsQuickActionOpen(false); setActiveView('team'); }} className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:text-indigo-600 transition-colors">
                                            <ShieldCheck className="w-4 h-4 text-gray-400" /> Add Co-worker
                                        </button>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </div>
                </header>

                {/* View Content Container */}
                <div className="p-6 md:p-10 max-w-7xl mx-auto min-h-[calc(100vh-80px)]">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={activeView}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            transition={{ duration: 0.2 }}
                            className="h-full"
                        >
                            {renderView()}
                        </motion.div>
                    </AnimatePresence>
                </div>
            </main>

        </div>
    );
};

export default AdminDashboard;

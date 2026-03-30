import React, { useEffect, useState, useRef } from 'react';
import { motion as Motion, AnimatePresence } from 'framer-motion';
import {
    LayoutDashboard, BookOpen, CalendarClock, History,
    Bell, Settings, User as UserIcon, LifeBuoy,
    LogOut, Clock, ArrowRight, PlayCircle, Activity,
    ShieldCheck, GraduationCap, X, ChevronRight, CheckCircle2,
    Calendar, MapPin, Building2, UploadCloud, Download, ChevronDown,
    Camera, Mail, Phone, Lock, Shield, HelpCircle, MessageSquare, Plus,
    CreditCard, Globe, BellRing
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useBackend } from '../contexts/BackendContext';

const defaultUser = {
    candidate_id: null,
    name: 'Candidate',
    firstName: 'Candidate',
    lastName: '',
    email: '',
    role: 'Candidate',
    mobile_no: '',
    photo_url: '',
    country: '',
    timezone: '',
    years_of_experience: 0,
};

const navigation = [
    { id: 'overview', name: 'Overview', icon: LayoutDashboard },
    { id: 'available', name: 'Discover Exams', icon: BookOpen },
    { id: 'scheduled', name: 'Upcoming', icon: CalendarClock },
    { id: 'history', name: 'History', icon: History },
];

const upcomingExam = {
    title: "Senior Frontend Assessment",
    company: "TechCorp Inc.",
    date: "Tomorrow",
    time: "10:00 AM PST",
    duration: "120 mins",
    tags: ["Proctored", "React", "System Design"],
    logo: "TC"
};

const formatUpcomingHero = (exam) => {
    if (!exam) {
        return upcomingExam;
    }

    const examDate = exam.exam_date ? new Date(exam.exam_date) : null;
    const isValidDate = examDate && !Number.isNaN(examDate.getTime());

    return {
        title: exam.title || 'Upcoming Assessment',
        company: exam.organization || 'Organization',
        date: isValidDate ? examDate.toLocaleDateString() : 'TBA',
        time: isValidDate ? examDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'TBA',
        duration: `${exam.duration_minutes || 0} mins`,
        tags: [...(exam.specializations || []), ...(exam.key_topics || [])].slice(0, 4),
        logo: (exam.organization || 'OR').slice(0, 2).toUpperCase(),
    };
};

const recentActivity = [
    { title: "Passed 'React Native Screen'", time: "2 days ago", type: "success" },
    { title: "Identity Verification Approved", time: "1 week ago", type: "info" },
    { title: "System Maintenance Scheduled", time: "Oct 30", type: "warning" },
];

const examHistory = [
    { id: 1, title: "React Native Developer Test", date: "Sep 15, 2025", score: "92%", status: "Pass", certificate: true },
    { id: 2, title: "Python Data Science Screen", date: "Aug 02, 2025", score: "68%", status: "Fail", certificate: false },
    { id: 3, title: "System Design Interview II", date: "Jul 20, 2025", score: "88%", status: "Pass", certificate: true },
];

// --- Animations ---
const fadeUp = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 },
    transition: { type: "spring", stiffness: 300, damping: 30 }
};

const staggerContainer = {
    animate: {
        transition: {
            staggerChildren: 0.1
        }
    }
};

const itemVariant = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

const Dashboard = () => {
    const [view, setView] = useState('overview');
    const [user, setUser] = useState(defaultUser);
    const [profileForm, setProfileForm] = useState({
        firstName: '',
        lastName: '',
        email: '',
        mobile_no: '',
        role: 'Candidate',
    });
    const [profileSaving, setProfileSaving] = useState(false);
    const [photoUploading, setPhotoUploading] = useState(false);
    const [passwordForm, setPasswordForm] = useState({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
    });
    const [passwordSaving, setPasswordSaving] = useState(false);
    const [notifications, setNotifications] = useState([]);
    const [toast, setToast] = useState({ show: false, type: 'success', message: '' });
    const toastTimerRef = useRef(null);
    const [loading, setLoading] = useState(true);
    const [discoverExams, setDiscoverExams] = useState([]);
    const [upcomingExams, setUpcomingExams] = useState([]);
    const [examsLoading, setExamsLoading] = useState(false);
    const [registeringExamId, setRegisteringExamId] = useState(null);
    const [unregisteringExamId, setUnregisteringExamId] = useState(null);
    const [launchModalExam, setLaunchModalExam] = useState(null);
    const [launchCodeLoadingExamId, setLaunchCodeLoadingExamId] = useState(null);
    const [historyResults, setHistoryResults] = useState([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const navigate = useNavigate();
    const { BACKEND_URL } = useBackend();

    useEffect(() => {
        const token = localStorage.getItem('access_token');

        if (!token) {
            navigate('/login');
            return;
        }

        const loadDashboardUser = async () => {
            try {
                const sessionResponse = await fetch(`${BACKEND_URL}/auth/me`, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });

                if (!sessionResponse.ok) {
                    throw new Error('Session expired');
                }

                const session = await sessionResponse.json();
                localStorage.setItem('candidate_id', String(session.candidate_id));

                const profileResponse = await fetch(`${BACKEND_URL}/candidate/profile/${session.candidate_id}`);
                const profile = profileResponse.ok ? await profileResponse.json() : {};

                const fullName = (profile.full_name || '').trim();
                const [firstName = 'Candidate', ...rest] = fullName ? fullName.split(' ') : ['Candidate'];
                const lastName = rest.join(' ');

                setUser({
                    candidate_id: session.candidate_id,
                    name: fullName || firstName,
                    firstName,
                    lastName,
                    email: profile.email || session.email || '',
                    role: session.role ? `${session.role.charAt(0).toUpperCase()}${session.role.slice(1)}` : 'Candidate',
                    mobile_no: profile.mobile_no || '',
                    photo_url: profile.photo_url || '',
                    country: profile.country || '',
                    timezone: profile.timezone || '',
                    years_of_experience: profile.years_of_experience ?? 0,
                });

                setProfileForm({
                    firstName,
                    lastName,
                    email: profile.email || session.email || '',
                    mobile_no: profile.mobile_no || '',
                    role: session.role ? `${session.role.charAt(0).toUpperCase()}${session.role.slice(1)}` : 'Candidate',
                });
            } catch (error) {
                console.error('Failed to load dashboard user:', error);
                localStorage.removeItem('access_token');
                localStorage.removeItem('candidate_id');
                navigate('/login');
            } finally {
                setLoading(false);
            }
        };

        loadDashboardUser();
    }, [BACKEND_URL, navigate]);

    useEffect(() => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            return;
        }

        const loadNotifications = async () => {
            try {
                const response = await fetch(`${BACKEND_URL}/auth/notifications/me`, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });

                if (!response.ok) {
                    return;
                }

                const data = await response.json();
                setNotifications(data.notifications || []);
            } catch (error) {
                console.error('Failed to load candidate notifications:', error);
            }
        };

        loadNotifications();
    }, [BACKEND_URL]);

    useEffect(() => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            return;
        }

        const loadCandidateExams = async () => {
            try {
                setExamsLoading(true);

                const [discoverResponse, upcomingResponse] = await Promise.all([
                    fetch(`${BACKEND_URL}/candidate/exams/discover`, {
                        headers: {
                            Authorization: `Bearer ${token}`,
                        },
                    }),
                    fetch(`${BACKEND_URL}/candidate/exams/upcoming`, {
                        headers: {
                            Authorization: `Bearer ${token}`,
                        },
                    }),
                ]);

                const discoverData = discoverResponse.ok ? await discoverResponse.json() : { exams: [] };
                const upcomingData = upcomingResponse.ok ? await upcomingResponse.json() : { exams: [] };

                setDiscoverExams(discoverData.exams || []);
                setUpcomingExams(upcomingData.exams || []);
            } catch (error) {
                console.error('Failed to load candidate exams:', error);
            } finally {
                setExamsLoading(false);
            }
        };

        loadCandidateExams();
    }, [BACKEND_URL]);

    useEffect(() => {
        if (view === 'available') {
            const token = localStorage.getItem('access_token');
            if (!token) {
                return;
            }

            const refreshDiscoverOnOpen = async () => {
                try {
                    setExamsLoading(true);
                    const [discoverResponse, upcomingResponse] = await Promise.all([
                        fetch(`${BACKEND_URL}/candidate/exams/discover`, {
                            headers: {
                                Authorization: `Bearer ${token}`,
                            },
                        }),
                        fetch(`${BACKEND_URL}/candidate/exams/upcoming`, {
                            headers: {
                                Authorization: `Bearer ${token}`,
                            },
                        }),
                    ]);

                    const discoverData = discoverResponse.ok ? await discoverResponse.json() : { exams: [] };
                    const upcomingData = upcomingResponse.ok ? await upcomingResponse.json() : { exams: [] };

                    setDiscoverExams(discoverData.exams || []);
                    setUpcomingExams(upcomingData.exams || []);
                } catch (error) {
                    console.error('Failed to refresh exams on discover open:', error);
                } finally {
                    setExamsLoading(false);
                }
            };

            refreshDiscoverOnOpen();
        }
    }, [view, BACKEND_URL]);

    useEffect(() => {
        if (view !== 'history') {
            return;
        }

        const token = localStorage.getItem('access_token');
        if (!token) {
            return;
        }

        const loadHistory = async () => {
            try {
                setHistoryLoading(true);
                const response = await fetch(`${BACKEND_URL}/candidate/history/results`, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });

                const data = response.ok ? await response.json() : { history: [] };
                setHistoryResults(data.history || []);
            } catch (error) {
                console.error('Failed to load candidate history:', error);
                setHistoryResults([]);
            } finally {
                setHistoryLoading(false);
            }
        };

        loadHistory();
    }, [view, BACKEND_URL]);

    const loadCandidateExams = async () => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            return;
        }

        try {
            setExamsLoading(true);
            const [discoverResponse, upcomingResponse] = await Promise.all([
                fetch(`${BACKEND_URL}/candidate/exams/discover`, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }),
                fetch(`${BACKEND_URL}/candidate/exams/upcoming`, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }),
            ]);

            const discoverData = discoverResponse.ok ? await discoverResponse.json() : { exams: [] };
            const upcomingData = upcomingResponse.ok ? await upcomingResponse.json() : { exams: [] };

            setDiscoverExams(discoverData.exams || []);
            setUpcomingExams(upcomingData.exams || []);
        } catch (error) {
            console.error('Failed to refresh candidate exams:', error);
        } finally {
            setExamsLoading(false);
        }
    };

    const registerForExam = async (examId) => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            navigate('/login');
            return;
        }

        try {
            setRegisteringExamId(examId);
            const response = await fetch(`${BACKEND_URL}/candidate/exams/${examId}/register`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                showToast(data.detail || 'Unable to register for exam', 'error');
                return;
            }

            showToast('Exam registration successful', 'success');
            await loadCandidateExams();
            setView('scheduled');
        } catch (error) {
            console.error('Exam registration failed:', error);
            showToast('Unable to register for exam', 'error');
        } finally {
            setRegisteringExamId(null);
        }
    };

    const unregisterFromExam = async (examId) => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            navigate('/login');
            return;
        }

        try {
            setUnregisteringExamId(examId);
            const response = await fetch(`${BACKEND_URL}/candidate/exams/${examId}/register`, {
                method: 'DELETE',
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                showToast(data.detail || 'Unable to unregister exam', 'error');
                return;
            }

            showToast('Exam unregistered successfully', 'success');
            await loadCandidateExams();
        } catch (error) {
            console.error('Exam unregister failed:', error);
            showToast('Unable to unregister exam', 'error');
        } finally {
            setUnregisteringExamId(null);
        }
    };

    const openLaunchExamModal = async (exam) => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            navigate('/login');
            return;
        }

        if (exam?.exam_launch_code) {
            setLaunchModalExam(exam);
            return;
        }

        try {
            setLaunchCodeLoadingExamId(exam.exam_id);
            const response = await fetch(`${BACKEND_URL}/candidate/exams/${exam.exam_id}/launch-code`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                showToast(data.detail || 'Unable to load launch code', 'error');
                return;
            }

            const enrichedExam = {
                ...exam,
                exam_launch_code: data.exam_launch_code || null,
                exam_launch_code_expires_at: data.exam_launch_code_expires_at || null,
            };

            setUpcomingExams((prev) =>
                prev.map((item) =>
                    item.exam_id === enrichedExam.exam_id ? { ...item, ...enrichedExam } : item
                )
            );
            setLaunchModalExam(enrichedExam);
        } catch (error) {
            console.error('Failed to fetch launch code:', error);
            showToast('Unable to load launch code', 'error');
        } finally {
            setLaunchCodeLoadingExamId(null);
        }
    };

    const closeLaunchExamModal = () => {
        setLaunchModalExam(null);
    };

    const copyLaunchCode = async () => {
        if (!launchModalExam?.exam_launch_code) {
            return;
        }
        try {
            await navigator.clipboard.writeText(launchModalExam.exam_launch_code);
            showToast('Launch code copied', 'success');
        } catch (error) {
            console.error('Failed to copy launch code:', error);
            showToast('Could not copy launch code', 'error');
        }
    };

    const downloadOfferLetter = async (resultId) => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            navigate('/login');
            return;
        }

        try {
            const response = await fetch(`${BACKEND_URL}/candidate/offers/${resultId}/download`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                showToast(errorData.detail || 'Unable to download offer letter', 'error');
                return;
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'offer-letter.pdf';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Offer download failed:', error);
            showToast('Unable to download offer letter', 'error');
        }
    };

    const nextUpcomingExam = upcomingExams
        .filter((exam) => exam.exam_date && !Number.isNaN(new Date(exam.exam_date).getTime()))
        .sort((a, b) => new Date(a.exam_date).getTime() - new Date(b.exam_date).getTime())[0]
        || upcomingExams[0]
        || null;

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

    const markAllNotificationsRead = async () => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            return;
        }

        const unread = notifications.filter((item) => !item.is_read);
        if (!unread.length) {
            return;
        }

        try {
            await Promise.all(
                unread.map((item) =>
                    fetch(`${BACKEND_URL}/auth/notifications/${item.notification_id}/read`, {
                        method: 'PATCH',
                        headers: {
                            Authorization: `Bearer ${token}`,
                        },
                    })
                )
            );

            setNotifications((prev) => prev.map((item) => ({ ...item, is_read: true })));
        } catch (error) {
            console.error('Failed to mark candidate notifications as read:', error);
        }
    };

    const handleProfileInput = (field, value) => {
        setProfileForm((prev) => ({ ...prev, [field]: value }));
    };

    const handlePasswordInput = (field, value) => {
        setPasswordForm((prev) => ({ ...prev, [field]: value }));
    };

    const showToast = (message, type = 'success') => {
        if (toastTimerRef.current) {
            clearTimeout(toastTimerRef.current);
        }

        setToast({ show: true, type, message });

        toastTimerRef.current = setTimeout(() => {
            setToast((prev) => ({ ...prev, show: false }));
        }, 3000);
    };

    const resetProfileForm = () => {
        setProfileForm({
            firstName: user.firstName || '',
            lastName: user.lastName || '',
            email: user.email || '',
            mobile_no: user.mobile_no || '',
            role: user.role || 'Candidate',
        });
    };

    const saveProfile = async () => {
        if (!user.candidate_id) {
            showToast('Candidate profile not available', 'error');
            return;
        }

        const fullName = `${profileForm.firstName} ${profileForm.lastName}`.trim();
        const email = profileForm.email.trim();
        const mobileNo = profileForm.mobile_no.trim();

        if (!fullName || !email) {
            showToast('Name and email are required', 'error');
            return;
        }

        try {
            setProfileSaving(true);
            const token = localStorage.getItem('access_token');

            const response = await fetch(`${BACKEND_URL}/candidate/profile`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    candidate_id: user.candidate_id,
                    full_name: fullName,
                    email,
                    mobile_no: mobileNo,
                }),
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok || data.error) {
                showToast(data.error || data.message || 'Failed to update profile', 'error');
                return;
            }

            const [firstName = 'Candidate', ...rest] = data.full_name.split(' ');
            const lastName = rest.join(' ');

            setUser((prev) => ({
                ...prev,
                name: data.full_name,
                firstName,
                lastName,
                email: data.email,
                mobile_no: data.mobile_no || '',
            }));

            setProfileForm((prev) => ({
                ...prev,
                firstName,
                lastName,
                email: data.email,
                mobile_no: data.mobile_no || '',
            }));

            showToast('Profile updated successfully', 'success');
        } catch (error) {
            console.error('Profile update failed:', error);
            showToast('Unable to update profile', 'error');
        } finally {
            setProfileSaving(false);
        }
    };

    const uploadProfilePhoto = async (file) => {
        if (!file || !user.candidate_id) {
            return;
        }

        try {
            setPhotoUploading(true);
            const token = localStorage.getItem('access_token');

            const payload = new FormData();
            payload.append('candidate_id', String(user.candidate_id));
            payload.append('photo', file);

            const response = await fetch(`${BACKEND_URL}/candidate/profile-photo`, {
                method: 'POST',
                headers: {
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: payload,
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok || data.error) {
                showToast(data.error || data.message || 'Failed to upload profile image', 'error');
                return;
            }

            setUser((prev) => ({
                ...prev,
                photo_url: data.photo_url || prev.photo_url,
            }));

            showToast('Profile photo updated', 'success');
        } catch (error) {
            console.error('Profile photo upload failed:', error);
            showToast('Unable to upload profile image', 'error');
        } finally {
            setPhotoUploading(false);
        }
    };

    const changePassword = async () => {
        const currentPassword = passwordForm.currentPassword.trim();
        const newPassword = passwordForm.newPassword.trim();
        const confirmPassword = passwordForm.confirmPassword.trim();

        if (!currentPassword || !newPassword || !confirmPassword) {
            showToast('Please fill all password fields', 'error');
            return;
        }

        if (newPassword.length < 6) {
            showToast('New password must be at least 6 characters', 'error');
            return;
        }

        if (newPassword !== confirmPassword) {
            showToast('New password and confirm password do not match', 'error');
            return;
        }

        try {
            setPasswordSaving(true);
            const token = localStorage.getItem('access_token');

            const response = await fetch(`${BACKEND_URL}/auth/change-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword,
                }),
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                showToast(data.detail || data.message || 'Unable to change password', 'error');
                return;
            }

            setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
            showToast('Password changed successfully', 'success');
        } catch (error) {
            console.error('Password change failed:', error);
            showToast('Unable to change password', 'error');
        } finally {
            setPasswordSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[#F8F9FA] text-gray-600">
                Loading dashboard...
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#F8F9FA] text-gray-900 font-sans selection:bg-indigo-500/30">
            {toast.show && (
                <div className="fixed top-6 right-6 z-[100]">
                    <div className={`px-4 py-3 rounded-xl shadow-lg border text-sm font-medium ${toast.type === 'success' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-rose-50 text-rose-800 border-rose-200'}`}>
                        {toast.message}
                    </div>
                </div>
            )}

            {/* Minimalist Top Navigation - Glassmorphism */}
            <header className="sticky top-0 z-50 w-full border-b border-gray-200/60 bg-white/70 backdrop-blur-2xl transition-all">
                <div className="max-w-[1400px] mx-auto px-6 h-20 flex items-center justify-between">
                    {/* Logo & Brand */}
                    <div className="flex items-center gap-12">
                        <img src="/logo.svg" alt="Observe" className="h-16" />

                        {/* Primary Nav Links */}
                        <nav className="hidden lg:flex items-center gap-2 p-1.5 rounded-2xl bg-gray-100/50 border border-gray-200/50 shadow-inner">
                            {navigation.map((item) => {
                                const active = view === item.id;
                                const Icon = item.icon;
                                return (
                                    <button
                                        key={item.id}
                                        onClick={() => {
                                            setView(item.id);
                                            if (item.id === 'available') {
                                                loadCandidateExams();
                                            }
                                        }}
                                        className={`relative px-5 py-2 rounded-xl text-sm font-medium transition-all duration-300 flex items-center gap-2 ${active ? 'text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-200/50'}`}
                                    >
                                        {active && (
                                            <Motion.div layoutId="nav-pill" className="absolute inset-0 bg-white rounded-xl shadow-[0_4px_12px_rgba(0,0,0,0.04)] border border-gray-200/50" />
                                        )}
                                        <span className="relative z-10 flex items-center gap-2">
                                            <Icon className={`w-4 h-4 ${active ? 'text-indigo-600' : ''}`} />
                                            {item.name}
                                        </span>
                                    </button>
                                );
                            })}
                        </nav>
                    </div>

                    {/* Right Side Tools */}
                    <div className="flex items-center gap-4 sm:gap-6">
                        {/* Notifications */}
                        <div className="relative group">
                            <button className="relative p-2.5 text-gray-500 hover:text-indigo-600 bg-gray-50 hover:bg-indigo-50 rounded-full transition-all border border-gray-200 shadow-sm hover:shadow">
                                <Bell className="w-5 h-5" />
                                {unreadCount > 0 && <span className="absolute top-0 right-0 w-3 h-3 bg-red-500 rounded-full border-2 border-white"></span>}
                            </button>
                            {/* Notification Dropdown (Hidden by default, hover to show) */}
                            <div className="absolute right-0 mt-2 w-80 bg-white rounded-2xl shadow-xl border border-gray-100 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 translate-y-2 group-hover:translate-y-0 z-50">
                                <div className="p-4 border-b border-gray-100 font-medium text-gray-900 flex justify-between items-center">
                                    Notifications
                                    <button onClick={markAllNotificationsRead} className="text-xs bg-indigo-50 text-indigo-600 px-2 py-1 rounded-md">{unreadCount} New</button>
                                </div>
                                <div className="p-2">
                                    {notifications.length === 0 && (
                                        <div className="p-3 text-sm text-gray-500">No notifications available.</div>
                                    )}
                                    {notifications.map((item) => (
                                        <div key={item.notification_id} className="p-3 hover:bg-gray-50 rounded-xl cursor-pointer transition-colors">
                                            <div className="text-sm font-medium text-gray-900">{item.title}</div>
                                            <div className="text-xs text-gray-500 mt-1">{item.body}</div>
                                            <div className="text-[10px] text-gray-400 mt-1">{formatNotificationTime(item.created_at)}</div>
                                        </div>
                                    ))}
                                </div>
                                <div className="p-3 border-t border-gray-100 text-center text-xs font-medium text-indigo-600 hover:bg-gray-50 cursor-pointer rounded-b-2xl">
                                    View All
                                </div>
                            </div>
                        </div>

                        <div className="h-8 w-px bg-gray-200"></div>

                        {/* User Profile */}
                        <div className="relative group">
                            <div className="flex items-center gap-3 cursor-pointer hover:bg-gray-50 p-1.5 pr-4 rounded-full transition-all border border-transparent hover:border-gray-200 hover:shadow-sm">
                                <div className="relative">
                                    <div className="w-10 h-10 rounded-full bg-indigo-50 border-2 border-white shadow-sm flex items-center justify-center text-indigo-500 overflow-hidden">
                                        {user.photo_url ? (
                                            <img src={user.photo_url} alt="Profile" className="w-full h-full object-cover" />
                                        ) : (
                                            <UserIcon className="w-5 h-5" />
                                        )}
                                    </div>
                                    <div className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-500 border-2 border-white rounded-full"></div>
                                </div>
                                <div className="hidden sm:block text-left relative z-10">
                                    <div className="text-sm font-medium leading-tight text-gray-900 group-hover:text-indigo-600 transition-colors">{user.name}</div>
                                    <div className="text-xs text-gray-500 font-medium">{user.role}</div>
                                </div>
                                <ChevronDown className="w-4 h-4 text-gray-400 group-hover:text-gray-600 hidden sm:block transition-transform group-hover:rotate-180" />
                            </div>

                            {/* User Dropdown */}
                            <div className="absolute right-0 mt-2 w-56 bg-white rounded-2xl shadow-xl border border-gray-100 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 translate-y-2 group-hover:translate-y-0 z-50">
                                <div className="p-2 border-b border-gray-100">
                                    <div onClick={() => setView('profile')} className="p-2 hover:bg-gray-50 rounded-xl cursor-pointer transition-colors flex items-center gap-3 text-sm font-medium text-gray-700">
                                        <UserIcon className="w-4 h-4" /> My Profile
                                    </div>
                                    <div onClick={() => setView('settings')} className="p-2 hover:bg-gray-50 rounded-xl cursor-pointer transition-colors flex items-center gap-3 text-sm font-medium text-gray-700">
                                        <Settings className="w-4 h-4" /> Settings
                                    </div>
                                    <div onClick={() => setView('support')} className="p-2 hover:bg-gray-50 rounded-xl cursor-pointer transition-colors flex items-center gap-3 text-sm font-medium text-gray-700">
                                        <LifeBuoy className="w-4 h-4" /> Support
                                    </div>
                                </div>
                                <div className="p-2">
                                    <div
                                        onClick={() => {
                                            localStorage.removeItem('access_token');
                                            localStorage.removeItem('candidate_id');
                                            navigate('/login');
                                        }}
                                        className="p-2 hover:bg-red-50 rounded-xl cursor-pointer transition-colors flex items-center gap-3 text-sm font-medium text-red-600"
                                    >
                                        <LogOut className="w-4 h-4" /> Sign Out
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content Area */}
            <main className="max-w-[1400px] mx-auto px-6 py-10 pb-24">
                <AnimatePresence mode="wait">
                    <Motion.div key={view} {...fadeUp} className="w-full">
                        {view === 'overview' && <BentoOverview setView={setView} user={user} upcomingExam={formatUpcomingHero(nextUpcomingExam)} />}
                        {view === 'available' && (
                            <DiscoverExamsView
                                exams={discoverExams}
                                loading={examsLoading}
                                registeringExamId={registeringExamId}
                                onRegister={registerForExam}
                            />
                        )}
                        {view === 'scheduled' && (
                            <UpcomingExamsView
                                exams={upcomingExams}
                                loading={examsLoading}
                                unregisteringExamId={unregisteringExamId}
                                onUnregister={unregisterFromExam}
                                onLaunchExam={openLaunchExamModal}
                                launchCodeLoadingExamId={launchCodeLoadingExamId}
                            />
                        )}
                        {view === 'history' && (
                            <ExamHistoryView
                                historyItems={historyResults}
                                loading={historyLoading}
                                onOfferDownload={downloadOfferLetter}
                            />
                        )}
                        {view === 'profile' && (
                            <ProfileView
                                user={user}
                                form={profileForm}
                                onChange={handleProfileInput}
                                onSave={saveProfile}
                                onCancel={resetProfileForm}
                                saving={profileSaving}
                                onPhotoUpload={uploadProfilePhoto}
                                photoUploading={photoUploading}
                            />
                        )}
                        {view === 'settings' && (
                            <SettingsView
                                passwordForm={passwordForm}
                                onPasswordChange={handlePasswordInput}
                                onPasswordSubmit={changePassword}
                                passwordSaving={passwordSaving}
                            />
                        )}
                        {view === 'support' && <SupportView />}
                    </Motion.div>
                </AnimatePresence>
            </main>

            <AnimatePresence>
                {launchModalExam && (
                    <Motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 bg-black/45 backdrop-blur-sm flex items-center justify-center p-4"
                        onClick={closeLaunchExamModal}
                    >
                        <Motion.div
                            initial={{ opacity: 0, y: 16, scale: 0.98 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: 12, scale: 0.98 }}
                            transition={{ type: 'spring', stiffness: 340, damping: 28 }}
                            className="w-full max-w-lg bg-white rounded-3xl shadow-2xl border border-gray-200/80 overflow-hidden"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="px-6 py-5 border-b border-gray-100 flex items-start justify-between gap-3">
                                <div>
                                    <h3 className="text-xl font-medium text-gray-900">Launch Exam</h3>
                                    <p className="text-sm text-gray-500 mt-1">Use this one-time code in the desktop EXE.</p>
                                </div>
                                <button
                                    onClick={closeLaunchExamModal}
                                    className="p-2 rounded-xl text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <div className="px-6 py-6 space-y-5">
                                <div>
                                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Exam</p>
                                    <p className="mt-1 text-base font-medium text-gray-900">{launchModalExam.title}</p>
                                    <p className="text-sm text-gray-500">{launchModalExam.organization}</p>
                                </div>

                                <div className="rounded-2xl border border-indigo-100 bg-indigo-50/70 px-4 py-4">
                                    <p className="text-xs font-medium text-indigo-700 uppercase tracking-wider mb-2">Unique Exam Code</p>
                                    <div className="font-mono text-3xl tracking-[0.25em] text-indigo-900 break-all">
                                        {launchModalExam.exam_launch_code || 'Not available'}
                                    </div>
                                </div>

                                <div className="text-sm text-gray-600 space-y-1">
                                    <p>
                                        <span className="font-medium text-gray-800">Expires:</span>{' '}
                                        {launchModalExam.exam_launch_code_expires_at
                                            ? new Date(launchModalExam.exam_launch_code_expires_at).toLocaleString()
                                            : 'Not set'}
                                    </p>
                                </div>
                            </div>

                            <div className="px-6 py-5 bg-gray-50 border-t border-gray-100 flex flex-col sm:flex-row gap-3 sm:justify-end">
                                <button
                                    onClick={copyLaunchCode}
                                    className="w-full sm:w-auto px-4 py-2.5 rounded-xl border border-gray-200 font-medium text-gray-700 hover:bg-gray-100 transition-colors"
                                >
                                    Copy Code
                                </button>
                                <button
                                    onClick={closeLaunchExamModal}
                                    className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-gray-900 text-white font-medium hover:bg-gray-800 transition-colors"
                                >
                                    Close
                                </button>
                            </div>
                        </Motion.div>
                    </Motion.div>
                )}
            </AnimatePresence>

        </div>
    );
};

// --- View 1: Bento Box Overview ---
const BentoOverview = ({ setView, user, upcomingExam }) => {
    return (
        <Motion.div variants={staggerContainer} initial="initial" animate="animate" className="grid grid-cols-1 md:grid-cols-12 auto-rows-[minmax(140px,auto)] gap-6">

            {/* Welcome Greeting Card (Span 8) - Dark Premium Card */}
            <Motion.div variants={itemVariant} className="md:col-span-8 bg-gradient-to-br from-gray-900 via-gray-900 to-black rounded-[2.5rem] p-10 text-white relative overflow-hidden shadow-2xl shadow-gray-900/10 flex flex-col justify-between group">
                {/* Animated Background Elements */}
                <div className="absolute -top-32 -right-32 w-96 h-96 bg-indigo-500/30 rounded-full blur-[80px] group-hover:bg-indigo-400/40 group-hover:scale-110 transition-all duration-700 ease-out"></div>
                <div className="absolute -bottom-32 -left-32 w-72 h-72 bg-emerald-500/20 rounded-full blur-[60px] group-hover:bg-emerald-400/30 group-hover:scale-110 transition-all duration-1000 ease-out"></div>

                <div className="absolute bottom-0 left-0 w-full h-1/2 bg-gradient-to-t from-black/50 to-transparent"></div>

                <div className="relative z-10 flex justify-between items-start">
                    <div>
                        <Motion.h1
                            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1, duration: 0.5 }}
                            className="text-4xl sm:text-5xl font-medium tracking-tight mb-3"
                        >
                            Welcome back,<br />{user.firstName || user.name}.
                        </Motion.h1>
                        <Motion.p
                            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2, duration: 0.5 }}
                            className="text-gray-400 font-medium text-lg max-w-sm"
                        >
                            You have <span className="text-white font-medium">1 upcoming exam</span> scheduled for tomorrow and <span className="text-white font-medium">1 action item</span> to review.
                        </Motion.p>
                    </div>

                    {/* Progress Circular Visualizer */}
                    <div className="hidden md:flex flex-col items-center justify-center p-6 bg-white/5 backdrop-blur-xl rounded-[2rem] border border-white/10 group-hover:bg-white/10 transition-colors shadow-inner relative overflow-hidden">
                        <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                        <div className="relative w-20 h-20 mb-3 group-hover:scale-105 transition-transform duration-500">
                            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                                <circle cx="50" cy="50" r="40" stroke="currentColor" strokeWidth="8" fill="none" className="text-gray-700" />
                                <Motion.circle
                                    initial={{ strokeDashoffset: 251.2 }}
                                    animate={{ strokeDashoffset: 62.8 }}
                                    transition={{ duration: 1.5, ease: "easeOut", delay: 0.5 }}
                                    cx="50" cy="50" r="40" stroke="currentColor" strokeWidth="8" fill="none"
                                    className="text-indigo-400 drop-shadow-[0_0_8px_rgba(129,140,248,0.5)]" strokeDasharray="251.2" strokeLinecap="round"
                                />
                            </svg>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <span className="text-xl font-medium text-white">75%</span>
                            </div>
                        </div>
                        <span className="text-xs font-medium text-gray-400 uppercase tracking-widest">Score Avg</span>
                    </div>
                </div>

                <div className="relative z-10 mt-12 flex items-center gap-4">
                    <button className="bg-white text-black px-8 py-4 rounded-2xl font-medium text-sm hover:scale-105 transition-transform flex items-center gap-3 shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:shadow-[0_0_25px_rgba(255,255,255,0.3)]">
                        <ShieldCheck className="w-5 h-5 text-indigo-600 animate-pulse" /> Run System Check
                    </button>
                    <button onClick={() => setView('scheduled')} className="bg-white/10 backdrop-blur-md border border-white/10 text-white px-8 py-4 rounded-2xl font-medium text-sm hover:bg-white/20 transition-colors flex items-center gap-2 group/btn">
                        View Schedule <ArrowRight className="w-4 h-4 ml-1 group-hover/btn:translate-x-1 transition-transform" />
                    </button>
                </div>
            </Motion.div>

            {/* Micro Bento Cards (Span 4) */}
            <Motion.div variants={itemVariant} className="md:col-span-4 grid grid-rows-2 gap-6">

                {/* Identity Verified Stat */}
                <div className="bg-white border text-gray-900 border-gray-200/60 rounded-[2.5rem] p-8 flex flex-col justify-between shadow-sm hover:shadow-lg hover:border-gray-300 transition-all duration-300 group">
                    <div className="flex items-start justify-between mb-4">
                        <div className="w-14 h-14 bg-emerald-50 text-emerald-500 rounded-2xl flex items-center justify-center group-hover:bg-emerald-500 group-hover:text-white transition-all duration-500 shadow-sm group-hover:shadow-[0_0_20px_rgba(16,185,129,0.3)] group-hover:-translate-y-1">
                            <ShieldCheck className="w-7 h-7" />
                        </div>
                        <span className="px-3 py-1 bg-green-50 text-emerald-700 text-[10px] font-medium uppercase tracking-widest rounded-lg border border-emerald-100 group-hover:scale-105 transition-transform">Verified</span>
                    </div>
                    <div>
                        <h3 className="text-gray-400 font-medium text-xs mb-1 uppercase tracking-widest">Identity Status</h3>
                        <div className="text-2xl font-medium text-gray-900 tracking-tight leading-tight group-hover:text-black transition-colors">Cleared for <br />Proctoring</div>
                    </div>
                </div>

                {/* Pending Actions */}
                <div className="bg-gradient-to-br from-indigo-50 to-white border border-indigo-100/60 rounded-[2.5rem] p-8 flex flex-col justify-between relative overflow-hidden group hover:shadow-lg hover:border-indigo-200 transition-all duration-500 cursor-pointer">
                    <div className="absolute -right-6 -bottom-6 opacity-[0.03] group-hover:opacity-10 group-hover:scale-110 group-hover:-rotate-12 transition-all duration-700 text-indigo-900">
                        <BookOpen className="w-40 h-40" />
                    </div>
                    <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-400/10 blur-[40px] rounded-full group-hover:bg-indigo-400/20 transition-all duration-700"></div>

                    <div className="relative z-10 lg:flex lg:flex-col lg:justify-between h-full">
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                                </span>
                                <h3 className="text-indigo-500 font-medium text-xs uppercase tracking-widest">New Invite</h3>
                            </div>
                            <div className="text-xl font-medium text-indigo-900 tracking-tight leading-tight line-clamp-2 mt-1">AWS Architect Pro Certification</div>
                        </div>
                        <div className="flex items-center gap-2 text-indigo-600 font-medium text-sm mt-4 lg:mt-0 group-hover:text-indigo-800 transition-colors bg-white/50 w-fit px-3 py-1.5 rounded-lg border border-indigo-50 backdrop-blur-sm group-hover:bg-white transition-all">
                            Accept Invite <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </div>
                    </div>
                </div>

            </Motion.div>

            {/* Upcoming Exam Hero Card (Span 8) */}
            <Motion.div variants={itemVariant} className="md:col-span-8 bg-white border border-gray-200/60 rounded-[1.5rem] p-6 sm:p-8 flex flex-col justify-between shadow-sm group hover:shadow-xl hover:border-indigo-200/60 transition-all duration-500 relative overflow-hidden">
                {/* Accent line that animates on hover */}
                <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-indigo-500 to-indigo-600 group-hover:w-2 transition-all duration-300"></div>
                {/* Subtle glowing background orb */}
                <div className="absolute -right-20 -top-20 w-64 h-64 bg-indigo-50 rounded-full blur-[60px] opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>

                <div className="relative z-10 flex items-center gap-2 mb-6">
                    <div className="relative flex items-center justify-center w-4 h-4">
                        <div className="absolute w-full h-full bg-indigo-400 rounded-full animate-ping opacity-20"></div>
                        <div className="w-2 h-2 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.8)]"></div>
                    </div>
                    <span className="text-indigo-600 font-medium text-xs uppercase tracking-widest">Next Scheduled Session</span>
                </div>

                <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-8 transform group-hover:translate-x-1 transition-transform duration-500">
                    <div>
                        <h2 className="text-2xl sm:text-3xl font-medium text-gray-900 mb-3 tracking-tight group-hover:text-black transition-colors">{upcomingExam.title}</h2>
                        <div className="flex flex-wrap items-center gap-3 text-gray-500 font-medium text-sm bg-gray-50/50 p-2 rounded-xl backdrop-blur-sm border border-gray-100/50 inline-flex">
                            <span className="flex items-center gap-1.5"><Calendar className="w-4 h-4 text-gray-400" /> {upcomingExam.date}</span>
                            <span className="text-gray-300">•</span>
                            <span className="flex items-center gap-1.5 text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md"><Clock className="w-3.5 h-3.5" /> {upcomingExam.time}</span>
                            <span className="text-gray-300">•</span>
                            <span className="flex items-center gap-1.5"><Activity className="w-4 h-4 text-gray-400" /> {upcomingExam.duration}</span>
                        </div>
                    </div>
                </div>

                <div className="relative z-10 flex flex-col sm:flex-row items-center gap-3 mt-auto pt-6 border-t border-gray-100">
                    <button className="w-full sm:w-auto bg-gray-900 text-white px-6 py-2.5 rounded-xl font-medium text-sm hover:bg-gray-800 transition-all flex items-center justify-center gap-2 shadow-sm group/btn hover:shadow-lg hover:-translate-y-0.5">
                        <PlayCircle className="w-4 h-4 group-hover/btn:text-indigo-400 transition-colors" /> Enter Waiting Room
                    </button>
                    <button className="w-full sm:w-auto px-6 py-2.5 rounded-xl border border-gray-200 font-medium text-gray-600 text-sm hover:bg-gray-50 hover:border-gray-300 transition-colors">
                        Reschedule
                    </button>
                </div>
            </Motion.div>

            {/* Activity Feed (Span 4) */}
            <Motion.div variants={itemVariant} className="md:col-span-4 bg-white border border-gray-200/60 rounded-[1.5rem] p-6 flex flex-col shadow-sm hover:shadow-lg hover:border-gray-300 transition-all duration-500 relative overflow-hidden group">
                {/* Subtle gradient overlay on hover */}
                <div className="absolute inset-0 bg-gradient-to-b from-gray-50/0 to-gray-50/50 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"></div>

                <div className="relative z-10 flex items-center justify-between mb-6">
                    <h3 className="text-sm font-medium text-gray-900 tracking-tight flex items-center gap-2">
                        <BellRing className="w-4 h-4 text-gray-400" /> Recent Activity
                    </h3>
                    <button className="text-xs font-medium text-indigo-600 hover:text-indigo-800 transition-colors flex items-center gap-1 group/link">
                        View All <ChevronRight className="w-3 h-3 group-hover/link:translate-x-0.5 transition-transform" />
                    </button>
                </div>

                <Motion.div
                    variants={staggerContainer} initial="initial" animate="animate"
                    className="relative z-10 space-y-4 relative before:absolute before:inset-0 before:ml-[5px] before:-translate-x-px before:h-full before:w-[2px] before:bg-gradient-to-b before:from-transparent before:via-gray-100 before:to-transparent"
                >
                    {recentActivity.map((item, i) => (
                        <Motion.div key={i} variants={itemVariant} className="relative flex items-start gap-4 group/item hover:-translate-y-0.5 transition-transform duration-300 cursor-default">
                            <div className={`mt-1 flex items-center justify-center w-3 h-3 rounded-full shrink-0 ${item.type === 'success' ? 'bg-emerald-500 outline-emerald-100 group-hover/item:shadow-[0_0_10px_rgba(16,185,129,0.4)]' : item.type === 'warning' ? 'bg-amber-500 outline-amber-100 group-hover/item:shadow-[0_0_10px_rgba(245,158,11,0.4)]' : 'bg-indigo-500 outline-indigo-100 group-hover/item:shadow-[0_0_10px_rgba(99,102,241,0.4)]'} outline outline-4 z-10 transition-shadow duration-300`}></div>
                            <div className="flex-1 pb-1 border-b border-gray-50 last:border-0 group-hover/item:border-transparent transition-colors">
                                <div className="font-medium text-gray-800 text-sm leading-snug mb-0.5 group-hover/item:text-black transition-colors">{item.title}</div>
                                <div className="text-xs text-gray-400 font-medium">{item.time}</div>
                            </div>
                        </Motion.div>
                    ))}
                </Motion.div>
            </Motion.div>

        </Motion.div>
    );
};

// --- View 2: Discover Exams ---
const DiscoverExamsView = ({ exams, loading, registeringExamId, onRegister }) => {
    const formatDateTime = (value) => {
        if (!value) {
            return 'TBA';
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return 'TBA';
        }
        return date.toLocaleString();
    };

    const isExamCompleted = (exam) => {
        if (typeof exam.is_test_completed === 'boolean') {
            return exam.is_test_completed;
        }

        const now = new Date();

        if (exam.end_date) {
            const endDate = new Date(`${exam.end_date}T23:59:59`);
            if (!Number.isNaN(endDate.getTime()) && endDate < now) {
                return true;
            }
        }

        return false;
    };

    return (
        <Motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-8">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-medium text-gray-900 tracking-tight">Discover Exams</h2>
                    <p className="text-gray-500 font-medium mt-1">Browse published exams from all organizations and register instantly.</p>
                </div>
            </div>

            {loading ? (
                <div className="bg-white rounded-[2rem] border border-gray-200/60 p-8 text-gray-500 font-medium">Loading exams...</div>
            ) : exams.length === 0 ? (
                <div className="bg-white rounded-[2rem] border border-gray-200/60 p-8 text-gray-500 font-medium">No published exams available right now.</div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {exams.map((exam) => {
                        const tags = [...(exam.specializations || []), ...(exam.key_topics || [])];
                        const isRegistered = Boolean(exam.registered);
                        const isCompleted = isExamCompleted(exam);
                        return (
                            <Motion.div key={exam.exam_id} variants={itemVariant} className={`rounded-[2rem] border p-8 shadow-sm transition-all duration-300 flex flex-col group ${isCompleted ? 'bg-gray-50 border-gray-300/70' : 'bg-white border-gray-200/60 hover:shadow-xl hover:-translate-y-1'}`}>
                                <div className="flex items-start justify-between mb-6 gap-3">
                                    <div className={`px-3 py-1 rounded-lg text-[10px] font-medium uppercase tracking-widest ${exam.exam_type === 'Certification' ? 'bg-amber-50 text-amber-600 border border-amber-100' : 'bg-indigo-50 text-indigo-600 border border-indigo-100'}`}>
                                        {exam.exam_type || 'Exam'}
                                    </div>
                                    {isCompleted ? (
                                        <div className="text-xs font-bold text-rose-600 bg-rose-50 border border-rose-200 px-2.5 py-1 rounded-lg text-right">
                                            Test Completed
                                        </div>
                                    ) : (
                                        <div className="text-xs font-medium text-gray-400 flex items-center gap-1 text-right">
                                            <Activity className="w-3 h-3" /> {exam.generation_mode || 'static'}
                                        </div>
                                    )}
                                </div>

                                <h3 className="text-xl font-medium text-gray-900 mb-2 leading-tight group-hover:text-indigo-600 transition-colors">{exam.title}</h3>
                                <p className="text-sm font-medium text-gray-500 flex items-center gap-2 mb-2"><Building2 className="w-4 h-4" /> {exam.organization}</p>
                                <p className="text-xs text-gray-500 font-medium mb-4 line-clamp-2">{exam.description || 'No description provided.'}</p>

                                <div className="grid grid-cols-2 gap-2 text-xs mb-5">
                                    {/* <div className="px-2.5 py-2 rounded-lg bg-gray-50 border border-gray-100 text-gray-600 font-medium">Duration: {exam.duration_minutes || 0}m</div> */}
                                    {/* <div className="px-2.5 py-2 rounded-lg bg-gray-50 border border-gray-100 text-gray-600 font-medium">Sections: {exam.section_count || 0}</div> */}
                                    <div className="px-2.5 py-2 rounded-lg bg-gray-50 border border-gray-100 text-gray-600 font-medium">Max Marks: {exam.max_marks || 0}</div>
                                    <div className="px-2.5 py-2 rounded-lg bg-gray-50 border border-gray-100 text-gray-600 font-medium">Attempts: {exam.max_attempts || 1}</div>
                                </div>

                                <div className="text-xs text-gray-500 font-medium mb-5 space-y-1.5">
                                    <div className="flex items-center gap-2"><Calendar className="w-3.5 h-3.5" /> Exam: {formatDateTime(exam.exam_date)}</div>
                                    <div className="flex items-center gap-2"><CalendarClock className="w-3.5 h-3.5" /> Window: {exam.start_date || 'TBA'} to {exam.end_date || 'TBA'}</div>
                                </div>

                                {tags.length > 0 && (
                                    <div className="flex flex-wrap gap-2 mb-8">
                                        {tags.map((tag, t) => (
                                            <span key={t} className="px-3 py-1 bg-gray-50 text-gray-600 rounded-lg text-xs font-medium">{tag}</span>
                                        ))}
                                    </div>
                                )}

                                <div className="mt-auto flex items-center justify-between pt-6 border-t border-gray-100">
                                    <div className="flex items-center gap-2 text-gray-500 font-medium text-sm">
                                        <Clock className="w-4 h-4" /> {exam.duration_minutes || 0} mins
                                    </div>
                                    <button
                                        onClick={() => onRegister(exam.exam_id)}
                                        disabled={isCompleted || isRegistered || registeringExamId === exam.exam_id}
                                        className="bg-gray-900 text-white px-5 py-2.5 rounded-xl font-medium text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-md disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                                    >
                                        {isCompleted ? 'Test Completed' : isRegistered ? 'Registered' : registeringExamId === exam.exam_id ? 'Registering...' : 'Register'}
                                    </button>
                                </div>
                            </Motion.div>
                        );
                    })}
                </div>
            )}
        </Motion.div>
    );
};

// --- View 3: Upcoming Exams ---
const UpcomingExamsView = ({ exams, loading, unregisteringExamId, onUnregister, onLaunchExam, launchCodeLoadingExamId }) => {
    const formatDate = (value) => {
        if (!value) {
            return 'TBA';
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return 'TBA';
        }
        return date.toLocaleDateString();
    };

    const formatTime = (value) => {
        if (!value) {
            return 'TBA';
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return 'TBA';
        }
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    return (
        <Motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-8 max-w-5xl mx-auto">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 mb-10">
                <div>
                    <h2 className="text-3xl font-medium text-gray-900 tracking-tight">Your Schedule</h2>
                    <p className="text-gray-500 font-medium mt-1">Registered exams from all organizations appear here.</p>
                </div>
            </div>

            {loading ? (
                <div className="bg-white rounded-[1.5rem] border border-gray-200/60 p-6 text-gray-500 font-medium">Loading upcoming exams...</div>
            ) : exams.length === 0 ? (
                <div className="bg-white rounded-[1.5rem] border border-gray-200/60 p-6 text-gray-500 font-medium">No registered exams yet.</div>
            ) : (
                <div className="space-y-4">
                    {exams.map((exam) => {
                        const tags = [...(exam.specializations || []), ...(exam.key_topics || [])];
                        const logo = (exam.organization || 'ORG').slice(0, 2).toUpperCase();
                        return (
                            <Motion.div key={exam.registration_id || exam.exam_id} variants={itemVariant} className="bg-white rounded-[1.5rem] border border-gray-200/60 p-5 sm:p-6 flex flex-col lg:flex-row items-start lg:items-center gap-5 sm:gap-6 shadow-sm hover:shadow-md transition-all group relative overflow-hidden">
                                <div className="absolute left-0 top-0 w-1.5 h-full bg-indigo-500 group-hover:w-2 transition-all"></div>

                                <div className="flex flex-col sm:items-center sm:justify-center gap-1 min-w-[120px] lg:w-32 shrink-0 pl-4 border-b lg:border-b-0 lg:border-r border-gray-100 pb-4 lg:pb-0">
                                    <span className="text-xs font-medium text-gray-400 uppercase tracking-widest">{formatDate(exam.exam_date)}</span>
                                    <span className="text-2xl font-medium text-indigo-600">{formatTime(exam.exam_date)}</span>
                                </div>

                                <div className="flex-1 w-full lg:px-4">
                                    <div className="flex items-center gap-3 mb-2">
                                        <span className="text-sm font-medium text-gray-500 flex items-center gap-2">
                                            <span className="w-5 h-5 rounded-md bg-gray-50 flex items-center justify-center text-[10px] font-medium text-gray-400 border border-gray-100">{logo}</span>
                                            {exam.organization}
                                        </span>
                                    </div>
                                    <h3 className="text-xl font-medium text-gray-900 group-hover:text-black transition-colors mb-2 leading-tight pr-4">{exam.title}</h3>
                                    <p className="text-xs text-gray-500 font-medium mb-3">{exam.exam_type || 'Exam'} • {exam.duration_minutes || 0} mins • {exam.max_marks || 0} marks</p>
                                    {tags.length > 0 && (
                                        <div className="flex flex-wrap gap-2">
                                            {tags.map((tag, t) => (
                                                <span key={t} className="px-2.5 py-1 bg-gray-50 border border-gray-100 text-gray-500 rounded-md text-[11px] font-medium uppercase tracking-wide">{tag}</span>
                                            ))}
                                        </div>
                                    )}
                                </div>

                                <div className="flex flex-col sm:flex-row items-center gap-3 w-full lg:w-auto shrink-0 border-t lg:border-t-0 border-gray-100 pt-5 lg:pt-0">
                                    <button
                                        onClick={() => onLaunchExam(exam)}
                                        disabled={launchCodeLoadingExamId === exam.exam_id}
                                        className="w-full sm:w-auto px-5 py-2.5 rounded-xl border border-gray-200 font-medium text-gray-700 text-sm hover:bg-gray-100 transition-colors whitespace-nowrap disabled:opacity-60 disabled:cursor-not-allowed"
                                    >
                                        {launchCodeLoadingExamId === exam.exam_id ? 'Loading Code...' : 'Launch Exam'}
                                    </button>
                                    <button
                                        onClick={() => onUnregister(exam.exam_id)}
                                        disabled={unregisteringExamId === exam.exam_id}
                                        className="w-full sm:w-auto bg-rose-600 text-white px-6 py-2.5 rounded-xl font-medium text-sm hover:bg-rose-500 transition-all flex items-center justify-center gap-2 shadow-sm group/btn hover:-translate-y-0.5 whitespace-nowrap disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                                    >
                                        <X className="w-4 h-4" /> {unregisteringExamId === exam.exam_id ? 'Unregistering...' : 'Unregister'}
                                    </button>
                                </div>
                            </Motion.div>
                        );
                    })}
                </div>
            )}
        </Motion.div>
    );
};

// --- View 4: Exam History ---
const ExamHistoryView = ({ historyItems, loading, onOfferDownload }) => (
    <Motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-8 max-w-5xl mx-auto">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 mb-10">
            <div>
                <h2 className="text-3xl font-medium text-gray-900 tracking-tight">Exam History</h2>
                <p className="text-gray-500 font-medium mt-1">Review your published exam results and offer letters.</p>
            </div>
        </div>

        <div className="space-y-4">
            {loading && (
                <div className="bg-white rounded-[1.5rem] border border-gray-200/60 p-6 text-gray-500 font-medium">Loading history...</div>
            )}
            {!loading && historyItems.length === 0 && (
                <div className="bg-white rounded-[1.5rem] border border-gray-200/60 p-6 text-gray-500 font-medium">No published results available yet.</div>
            )}
            {!loading && historyItems.map((item) => {
                const statusLabel = item.status || 'Pending Eval';
                const isPass = statusLabel === 'Pass';
                const scoreText = item.score === null || item.score === undefined ? '-' : `${item.score}%`;
                const scoreValue = Number(item.score || 0);
                const widthValue = Number.isFinite(scoreValue) ? Math.max(0, Math.min(100, scoreValue)) : 0;
                const dateText = item.date ? new Date(item.date).toLocaleDateString() : 'N/A';

                return (
                <Motion.div key={item.result_id} variants={itemVariant} className="bg-white rounded-[1.5rem] border border-gray-200/60 p-5 sm:p-6 flex flex-col lg:flex-row items-start lg:items-center gap-5 sm:gap-6 shadow-sm hover:shadow-md transition-all group">

                    {/* Left Info Group (Flex to fill) */}
                    <div className="flex items-center gap-4 sm:gap-5 flex-1 w-full lg:w-auto overflow-hidden">
                        <div className={`hidden sm:flex w-12 h-12 rounded-xl items-center justify-center shrink-0 border ${isPass ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : 'bg-rose-50 text-rose-600 border-rose-100'}`}>
                            {isPass ? <ShieldCheck className="w-6 h-6" /> : <X className="w-6 h-6" />}
                        </div>
                        <div className="truncate w-full pr-4 lg:pr-8">
                            <h3 className="text-lg font-medium text-gray-900 group-hover:text-black transition-colors mb-1 truncate">{item.title}</h3>
                            <div className="flex items-center gap-2 text-sm font-medium text-gray-400">
                                <Calendar className="w-4 h-4" /> {dateText}
                            </div>
                        </div>
                    </div>

                    {/* Right Action Groups (Fixed widths for vertical alignment) */}
                    <div className="flex flex-col sm:flex-row items-center gap-5 lg:gap-8 w-full lg:w-auto border-t lg:border-t-0 border-gray-100 pt-5 lg:pt-0">
                        {/* Score Block */}
                        <div className="flex items-center gap-4 w-full sm:w-40 lg:w-48 shrink-0">
                            <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                                <div
                                    className={`h-full rounded-full transition-all duration-1000 ${isPass ? 'bg-emerald-500' : 'bg-rose-500'}`}
                                    style={{ width: `${widthValue}%` }}
                                />
                            </div>
                            <span className="font-medium text-xl text-gray-900 w-12 text-right">{scoreText}</span>
                        </div>

                        {/* Status Badge */}
                        <div className="w-full sm:w-28 lg:w-32 shrink-0 flex sm:justify-center">
                            <div className={`px-4 py-2 rounded-lg text-xs font-medium uppercase tracking-wider inline-flex justify-center ${isPass ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>
                                {statusLabel}
                            </div>
                        </div>

                        {/* Certificate Action */}
                        <div className="w-full lg:w-auto min-w-[120px] shrink-0 flex justify-end">
                            {isPass ? (
                                <button onClick={() => onOfferDownload(item.result_id)} className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-gray-900 text-white rounded-xl text-sm font-medium hover:bg-gray-800 transition-all shadow-sm group/btn hover:-translate-y-0.5 whitespace-nowrap">
                                    <Download className="w-4 h-4 group-hover/btn:scale-110 transition-transform" /> Offer Download
                                </button>
                            ) : (
                                <span className="inline-flex w-full sm:w-auto items-center justify-center px-5 py-2.5 text-sm font-medium text-gray-400 whitespace-nowrap">
                                    N/A
                                </span>
                            )}
                        </div>
                    </div>
                </Motion.div>
                );
            })}
        </div>
    </Motion.div>
);

// --- View 5: Profile ---
const ProfileView = ({ user, form, onChange, onSave, onCancel, saving, onPhotoUpload, photoUploading }) => (
    <Motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-8 max-w-4xl mx-auto">
        <div>
            <h2 className="text-3xl font-medium text-gray-900 tracking-tight">My Profile</h2>
            <p className="text-gray-500 font-medium mt-1">Manage your personal information and professional details.</p>
        </div>

        <Motion.div variants={itemVariant} className="bg-white rounded-[2rem] border border-gray-200/60 shadow-sm p-8 sm:p-10">
            {/* Avatar Section */}
            <div className="flex flex-col sm:flex-row items-center gap-6 mb-10 pb-10 border-b border-gray-100">
                <div className="relative group cursor-pointer">
                    <div className="w-24 h-24 rounded-full bg-indigo-50 border-4 border-white shadow-md flex items-center justify-center text-indigo-500 overflow-hidden">
                        {user.photo_url ? (
                            <img src={user.photo_url} alt="Profile" className="w-full h-full object-cover" />
                        ) : (
                            <UserIcon className="w-10 h-10 group-hover:scale-110 transition-transform" />
                        )}
                        <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                            <Camera className="w-6 h-6 text-white" />
                        </div>
                    </div>
                </div>
                <div className="text-center sm:text-left">
                    <h3 className="text-2xl font-medium text-gray-900 mb-1">{user.name}</h3>
                    <p className="text-gray-500 font-medium">{user.role}</p>
                    <div className="mt-4 flex flex-wrap justify-center sm:justify-start gap-3">
                        <label className="px-4 py-2 bg-gray-900 text-white rounded-xl text-xs font-medium shadow hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 cursor-pointer">
                            {photoUploading ? 'Uploading...' : 'Upload New Picture'}
                            <input
                                type="file"
                                className="hidden"
                                accept="image/*"
                                onChange={(e) => onPhotoUpload(e.target.files?.[0] || null)}
                            />
                        </label>
                    </div>
                </div>
            </div>

            {/* Form Section */}
            <form className="space-y-8" onSubmit={(e) => {
                e.preventDefault();
                onSave();
            }}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <label className="text-xs font-medium text-gray-400 uppercase tracking-widest">First Name</label>
                        <input type="text" value={form.firstName} onChange={(e) => onChange('firstName', e.target.value)} className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all" />
                    </div>
                    <div className="space-y-2">
                        <label className="text-xs font-medium text-gray-400 uppercase tracking-widest">Last Name</label>
                        <input type="text" value={form.lastName} onChange={(e) => onChange('lastName', e.target.value)} className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all" />
                    </div>
                    <div className="space-y-2 md:col-span-2">
                        <label className="text-xs font-medium text-gray-400 uppercase tracking-widest">Email Address</label>
                        <div className="relative">
                            <input type="email" value={form.email} onChange={(e) => onChange('email', e.target.value)} className="w-full pl-11 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all" />
                            <Mail className="w-5 h-5 text-gray-400 absolute left-4 top-1/2 -translate-y-1/2" />
                        </div>
                    </div>
                    <div className="space-y-2 md:col-span-2">
                        <label className="text-xs font-medium text-gray-400 uppercase tracking-widest">Phone Number</label>
                        <div className="relative">
                            <input type="tel" value={form.mobile_no} onChange={(e) => onChange('mobile_no', e.target.value)} className="w-full pl-11 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all" />
                            <Phone className="w-5 h-5 text-gray-400 absolute left-4 top-1/2 -translate-y-1/2" />
                        </div>
                    </div>
                    {/* <div className="space-y-2 md:col-span-2">
                        <label className="text-xs font-medium text-gray-400 uppercase tracking-widest">Professional Title / Role</label>
                        <input type="text" value={form.role} readOnly className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all" />
                    </div> */}
                </div>

                <div className="pt-6 border-t border-gray-100 flex justify-end gap-3">
                    <button type="button" onClick={onCancel} className="px-6 py-3 bg-white border border-gray-200 text-gray-600 rounded-xl font-medium hover:bg-gray-100 transition-colors">Cancel</button>
                    <button disabled={saving} type="submit" className="px-6 py-3 bg-gray-900 text-white rounded-xl font-medium shadow-md hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 disabled:opacity-70 disabled:cursor-not-allowed">{saving ? 'Saving...' : 'Save Changes'}</button>
                </div>
            </form>
        </Motion.div>
    </Motion.div>
);

// --- View 6: Settings ---
const SettingsView = ({ passwordForm, onPasswordChange, onPasswordSubmit, passwordSaving }) => (
    <Motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-8 max-w-4xl mx-auto">
        <div>
            <h2 className="text-3xl font-medium text-gray-900 tracking-tight">Account Settings</h2>
            <p className="text-gray-500 font-medium mt-1">Manage your security preferences and notification configurations.</p>
        </div>

        {/* Security Section */}
        <Motion.div variants={itemVariant} className="bg-white rounded-[2rem] border border-gray-200/60 shadow-sm overflow-hidden">
            <div className="p-8 border-b border-gray-100 flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-600">
                    <Shield className="w-6 h-6" />
                </div>
                <div>
                    <h3 className="text-xl font-medium text-gray-900">Security & Privacy</h3>
                    <p className="text-sm font-medium text-gray-500 mt-1">Keep your account and exam data secure.</p>
                </div>
            </div>
            <div className="p-8 space-y-8">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div>
                        <h4 className="font-medium text-gray-900 mb-1">Two-Factor Authentication (2FA)</h4>
                        <p className="text-sm text-gray-500 font-medium">Add an extra layer of security to your account.</p>
                    </div>
                    <button className="px-5 py-2.5 bg-gray-900 text-white rounded-xl text-sm font-medium shadow hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 whitespace-nowrap">Enable 2FA</button>
                </div>
                <div className="h-px bg-gray-100"></div>
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div>
                        <h4 className="font-medium text-gray-900 mb-1">Update Password</h4>
                        <p className="text-sm text-gray-500 font-medium">Last changed 3 months ago.</p>
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <input
                        type="password"
                        placeholder="Current password"
                        value={passwordForm.currentPassword}
                        onChange={(e) => onPasswordChange('currentPassword', e.target.value)}
                        className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                    />
                    <input
                        type="password"
                        placeholder="New password"
                        value={passwordForm.newPassword}
                        onChange={(e) => onPasswordChange('newPassword', e.target.value)}
                        className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                    />
                    <input
                        type="password"
                        placeholder="Confirm new password"
                        value={passwordForm.confirmPassword}
                        onChange={(e) => onPasswordChange('confirmPassword', e.target.value)}
                        className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                    />
                </div>
                <div className="flex justify-end">
                    <button
                        onClick={onPasswordSubmit}
                        disabled={passwordSaving}
                        className="px-5 py-2.5 bg-white border border-gray-200 text-gray-700 rounded-xl text-sm font-medium shadow-sm hover:bg-gray-100 transition-colors whitespace-nowrap disabled:opacity-70 disabled:cursor-not-allowed"
                    >
                        {passwordSaving ? 'Updating...' : 'Change Password'}
                    </button>
                </div>
            </div>
        </Motion.div>

        {/* Notifications Section */}
        <Motion.div variants={itemVariant} className="bg-white rounded-[2rem] border border-gray-200/60 shadow-sm overflow-hidden">
            <div className="p-8 border-b border-gray-100 flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-amber-50 flex items-center justify-center text-amber-500">
                    <BellRing className="w-6 h-6" />
                </div>
                <div>
                    <h3 className="text-xl font-medium text-gray-900">Notification Preferences</h3>
                    <p className="text-sm font-medium text-gray-500 mt-1">Control how and when we send you alerts.</p>
                </div>
            </div>
            <div className="p-8 space-y-6">
                {['Exam Reminders', 'Score Postings', 'Security Alerts', 'Marketing Updates'].map((item, i) => (
                    <div key={i} className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                        <div>
                            <h4 className="font-medium text-gray-900">{item}</h4>
                            <p className="text-sm text-gray-500 mt-0.5">Receive via Email and Push.</p>
                        </div>
                        {/* Custom Toggle Switch */}
                        <div className={`w-12 h-6 rounded-full p-1 cursor-pointer transition-colors ${i === 3 ? 'bg-gray-200' : 'bg-emerald-500'}`}>
                            <div className={`w-4 h-4 rounded-full bg-white shadow-sm transform transition-transform ${i === 3 ? 'translate-x-0' : 'translate-x-6'}`}></div>
                        </div>
                    </div>
                ))}
            </div>
        </Motion.div>
    </Motion.div>
);

// --- View 7: Support ---
const SupportView = () => (
    <Motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-8 max-w-4xl mx-auto">
        <div>
            <h2 className="text-3xl font-medium text-gray-900 tracking-tight">Support Center</h2>
            <p className="text-gray-500 font-medium mt-1">Get help with your exams, platform issues, or general inquiries.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Quick Actions */}
            <Motion.div variants={itemVariant} className="bg-white rounded-[2rem] border border-gray-200/60 p-8 shadow-sm group hover:shadow-md transition-all cursor-pointer">
                <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-600 mb-6 group-hover:scale-110 transition-transform">
                    <MessageSquare className="w-7 h-7" />
                </div>
                <h3 className="text-xl font-medium text-gray-900 mb-2">Live Chat</h3>
                <p className="text-gray-500 text-sm font-medium mb-6">Talk to a support agent right now for immediate assistance.</p>
                <button className="text-indigo-600 font-medium text-sm flex items-center gap-2 group-hover:text-indigo-800 transition-colors">
                    Start Chat <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
            </Motion.div>

            <Motion.div variants={itemVariant} className="bg-white rounded-[2rem] border border-gray-200/60 p-8 shadow-sm group hover:shadow-md transition-all cursor-pointer">
                <div className="w-14 h-14 bg-emerald-50 rounded-2xl flex items-center justify-center text-emerald-600 mb-6 group-hover:scale-110 transition-transform">
                    <HelpCircle className="w-7 h-7" />
                </div>
                <h3 className="text-xl font-medium text-gray-900 mb-2">Knowledge Base</h3>
                <p className="text-gray-500 text-sm font-medium mb-6">Browse our comprehensive FAQs and documentation.</p>
                <button className="text-emerald-600 font-medium text-sm flex items-center gap-2 group-hover:text-emerald-800 transition-colors">
                    Visit FAQ <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
            </Motion.div>
        </div>

        {/* Support Ticket Form */}
        <Motion.div variants={itemVariant} className="bg-white rounded-[2rem] border border-gray-200/60 shadow-sm p-8 sm:p-10">
            <h3 className="text-2xl font-medium text-gray-900 mb-6">Submit a Support Ticket</h3>
            <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <label className="text-xs font-medium text-gray-400 uppercase tracking-widest">Issue Type</label>
                        <select className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all appearance-none cursor-pointer">
                            <option>Technical Issue (Platform)</option>
                            <option>Exam Scheduling</option>
                            <option>Billing & Payments</option>
                            <option>Account Access</option>
                            <option>Other</option>
                        </select>
                    </div>
                    <div className="space-y-2">
                        <label className="text-xs font-medium text-gray-400 uppercase tracking-widest">Priority</label>
                        <select className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all appearance-none cursor-pointer">
                            <option>Low</option>
                            <option>Medium</option>
                            <option>High</option>
                            <option>Urgent</option>
                        </select>
                    </div>
                    <div className="space-y-2 md:col-span-2">
                        <label className="text-xs font-medium text-gray-400 uppercase tracking-widest">Subject</label>
                        <input type="text" placeholder="Brief summary of your issue..." className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all" />
                    </div>
                    <div className="space-y-2 md:col-span-2">
                        <label className="text-xs font-medium text-gray-400 uppercase tracking-widest">Description</label>
                        <textarea rows="5" placeholder="Please provide all relevant details here..." className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all resize-none"></textarea>
                    </div>
                </div>

                <div className="pt-6 border-t border-gray-100 flex justify-end">
                    <button type="button" className="px-8 py-3 bg-gray-900 text-white rounded-xl font-medium shadow-md hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 flex items-center gap-2">
                        <UploadCloud className="w-4 h-4" /> Submit Ticket
                    </button>
                </div>
            </form>
        </Motion.div>
    </Motion.div>
);

export default Dashboard;



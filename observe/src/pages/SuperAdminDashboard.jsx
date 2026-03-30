import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { BACKEND_URL } from '../contexts/BackendContext';
import { ResponsiveContainer, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, LineChart, Line } from 'recharts';
import {
    LayoutDashboard, Building2, Users, UserCog, MonitorPlay, Activity,
    CreditCard, Settings, ShieldAlert, BellRing, Ticket, FileText,
    LogOut, Menu, Search, Plus, Filter, Edit2, Trash2, ArrowUpRight, ArrowDownRight,
    Lock, CheckCircle2, ShieldCheck, Mail, Phone, Globe, AlertTriangle, RefreshCw
} from 'lucide-react';

const API_BASE_URL = BACKEND_URL;

// --- Placeholder View ---
const PlaceholderView = ({ title, icon: Icon, description }) => (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="h-full flex flex-col items-center justify-center text-center p-10 bg-[#0a0a0a] border border-gray-800 rounded-[2rem] shadow-sm">
        <div className="w-16 h-16 bg-gray-900 rounded-2xl flex items-center justify-center mb-6 border border-gray-800">
            <Icon className="w-8 h-8 text-indigo-400" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">{title}</h2>
        <p className="text-gray-400 font-medium max-w-sm">{description || "This global management module is currently under active development."}</p>
    </motion.div>
);

// --- View 1: Global Dashboard ---
const GlobalDashboard = () => {
    const chartData = [
        { name: 'Mon', usage: 12000, capacity: 20000 },
        { name: 'Tue', usage: 15000, capacity: 20000 },
        { name: 'Wed', usage: 18000, capacity: 20000 },
        { name: 'Thu', usage: 14000, capacity: 20000 },
        { name: 'Fri', usage: 19500, capacity: 20000 },
        { name: 'Sat', usage: 8000,  capacity: 20000 },
        { name: 'Sun', usage: 6000,  capacity: 20000 },
    ];

    return (
        <div className="space-y-6">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-white">Platform Overview</h1>
                <p className="text-gray-400 font-medium mt-1">Real-time metrics across all registered organizations.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                {[
                    { label: "Total Organizations", value: "248", change: "+12", up: true },
                    { label: "Total Admins", value: "1,204", change: "+45", up: true },
                    { label: "Total Candidates", value: "854K", change: "+12K", up: true },
                    { label: "Total Exams", value: "3.2M", change: "+45K", up: true },
                    { label: "Active Exams", value: "1,402", change: "LIVE", alert: true },
                ].map((stat, i) => (
                    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.1 }} key={i} className={`bg-[#111] p-6 rounded-2xl border ${stat.alert ? 'border-amber-500/50 shadow-[0_0_15px_rgba(245,158,11,0.1)]' : 'border-gray-800'}`}>
                        <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">{stat.label}</p>
                        <div className="flex items-end justify-between">
                            <h3 className="text-3xl font-black text-white">{stat.value}</h3>
                            <span className={`flex items-center text-xs font-bold ${stat.alert ? 'text-amber-500 animate-pulse' : stat.up ? 'text-emerald-400' : 'text-red-400'}`}>
                                {!stat.alert && (stat.up ? <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" /> : <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />)}
                                {stat.change}
                            </span>
                        </div>
                    </motion.div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="lg:col-span-2 bg-[#111] p-6 rounded-2xl border border-gray-800 min-h-[400px] flex flex-col">
                    <h3 className="text-lg font-bold text-white mb-6">Global Platform Load</h3>
                    <div className="flex-1">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="colorUsage" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.4}/>
                                        <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#333" />
                                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6b7280' }} dy={10} />
                                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6b7280' }} />
                                <Tooltip contentStyle={{ backgroundColor: '#111', borderColor: '#333', color: '#fff', borderRadius: '12px' }} />
                                <Area type="monotone" dataKey="usage" stroke="#6366f1" strokeWidth={3} fillOpacity={1} fill="url(#colorUsage)" activeDot={{ r: 6, strokeWidth: 0, fill: '#6366f1' }} />
                                <Line type="step" dataKey="capacity" stroke="#ef4444" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-[#111] p-6 rounded-2xl border border-gray-800 flex flex-col">
                    <h3 className="text-lg font-bold text-white mb-6">Recent Anomaly Logs</h3>
                    <div className="flex-1 overflow-y-auto pr-2 space-y-4 scrollbar-hide">
                        {[
                            { time: "2m ago", type: "DDoS Attempt", org: "Global Edge", status: "Blocked" },
                            { time: "15m ago", type: "DB High Load", org: "System", status: "Scaling +2 Nodes" },
                            { time: "1h ago", type: "Mass Proctor Flag", org: "University Tech", status: "Investigating" },
                            { time: "3h ago", type: "API Rate Limit", org: "Acme Corp", status: "Throttled" },
                        ].map((log, i) => (
                            <div key={i} className="flex gap-4 p-3 rounded-xl bg-gray-900 border border-gray-800">
                                <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                                <div>
                                    <p className="text-sm font-bold text-white">{log.type}</p>
                                    <p className="text-xs font-medium text-gray-400 mt-0.5">{log.org}</p>
                                    <div className="flex items-center gap-2 mt-2 font-mono text-[10px] text-gray-500 uppercase tracking-wider">
                                        <span>{log.time}</span>
                                        <span>•</span>
                                        <span className={log.status === 'Blocked' || log.status === 'Throttled' ? 'text-emerald-400' : 'text-amber-400'}>{log.status}</span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </motion.div>
            </div>
        </div>
    );
};

// --- View 2: Organization Management ---
const OrgManagement = ({ organizations, loading, error, onOpenRegister, onEditOrganization, onDeleteOrganization }) => {
    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-white">Organization Management</h1>
                    <p className="text-gray-400 font-medium mt-1">Manage platform tenants, billing statuses, and global limits.</p>
                </div>
                <button onClick={onOpenRegister} className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-xl font-bold text-sm hover:bg-indigo-500 transition-all shadow-[0_0_15px_rgba(79,70,229,0.3)]">
                    <Plus className="w-4 h-4" /> Register Organization
                </button>
            </div>

            <div className="flex gap-3 bg-[#111] p-2 rounded-2xl border border-gray-800">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <input type="text" placeholder="Search organizations by ID, Name or Email..." className="w-full pl-9 pr-4 py-2 bg-[#1a1a1a] border border-gray-800 rounded-xl focus:ring-1 focus:ring-indigo-500 font-medium text-sm text-white placeholder:text-gray-600 outline-none transition-all" />
                </div>
                <button className="flex items-center gap-2 px-4 py-2 bg-[#1a1a1a] text-gray-400 border border-gray-800 rounded-xl font-medium text-sm hover:bg-gray-800 transition-colors">
                    <Filter className="w-4 h-4" /> Filter
                </button>
            </div>

            <div className="bg-[#111] rounded-2xl border border-gray-800 flex-1 overflow-hidden flex flex-col">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse min-w-[800px]">
                        <thead>
                            <tr className="bg-[#1a1a1a] border-b border-gray-800 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                <th className="p-4 pl-6">Organization</th>
                                <th className="p-4">Type</th>
                                <th className="p-4">Primary Contact</th>
                                <th className="p-4">Status</th>
                                <th className="p-4">Created Date</th>
                                <th className="p-4 pr-6 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800">
                            {loading && (
                                <tr>
                                    <td colSpan={6} className="p-8 text-center text-sm text-gray-500">Loading organizations...</td>
                                </tr>
                            )}

                            {!loading && error && (
                                <tr>
                                    <td colSpan={6} className="p-8 text-center text-sm text-red-400">{error}</td>
                                </tr>
                            )}

                            {!loading && !error && organizations.length === 0 && (
                                <tr>
                                    <td colSpan={6} className="p-8 text-center text-sm text-gray-500">No organizations registered yet.</td>
                                </tr>
                            )}

                            {!loading && !error && organizations.map((org, i) => (
                                <motion.tr initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }} key={org.id} className="hover:bg-gray-900 transition-colors">
                                    <td className="p-4 pl-6">
                                        <p className="font-bold text-sm text-white">{org.name}</p>
                                        <p className="text-xs font-mono text-gray-500 mt-0.5">{org.id}</p>
                                    </td>
                                    <td className="p-4"><span className="px-2.5 py-1 bg-gray-900 border border-gray-700 text-gray-300 rounded text-xs font-bold">{org.type}</span></td>
                                    <td className="p-4 text-sm text-gray-400 font-medium flex items-center gap-2"><Mail className="w-3 h-3"/> {org.email}</td>
                                    <td className="p-4">
                                        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-bold ${org.status === 'Active' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                                            {org.status}
                                        </span>
                                    </td>
                                    <td className="p-4 text-sm font-medium text-gray-500">{org.created}</td>
                                    <td className="p-4 pr-6 text-right">
                                        <button
                                            onClick={() => onEditOrganization(org)}
                                            className="p-2 text-gray-500 hover:text-indigo-400 hover:bg-gray-800 rounded-lg transition-colors"
                                        >
                                            <Edit2 className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={() => onDeleteOrganization(org)}
                                            className="p-2 text-gray-500 hover:text-red-400 hover:bg-gray-800 rounded-lg transition-colors"
                                        >
                                            <Trash2 className="w-4 h-4" />
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

// --- View 5: Global Exam Monitoring ---
const GlobalMonitoring = () => {
    const activeExams = [
        { id: "EX-992", org: "Global Tech University", title: "CS101 Final", candidates: 1250, flags: 42, status: "Live" },
        { id: "EX-884", org: "Acme Corporation", title: "Q3 Backend Hiring", candidates: 340, flags: 5, status: "Live" },
    ];

    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex justify-between items-center mb-4">
                <div>
                    <h1 className="text-2xl font-bold text-white">Global Exam Monitoring</h1>
                    <p className="text-gray-400 font-medium mt-1">Supervise running assessments across all tenants in real-time.</p>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                    <span className="text-sm font-bold text-red-400">1,590 Candidates Active</span>
                </div>
            </div>

            <div className="bg-[#111] rounded-2xl border border-gray-800 flex-1 overflow-hidden">
                 <table className="w-full text-left border-collapse min-w-[800px]">
                    <thead>
                        <tr className="bg-[#1a1a1a] border-b border-gray-800 text-xs font-bold text-gray-500 uppercase tracking-wider">
                            <th className="p-4 pl-6">Exam Identity</th>
                            <th className="p-4">Organization</th>
                            <th className="p-4 text-center">Active Candidates</th>
                            <th className="p-4 text-center">Proctor Flags</th>
                            <th className="p-4 pr-6 text-right">Super Override</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                        {activeExams.map((exam, i) => (
                            <tr key={i} className="hover:bg-gray-900 transition-colors">
                                <td className="p-4 pl-6">
                                    <p className="font-bold text-sm text-white">{exam.title}</p>
                                    <p className="text-xs font-mono text-gray-500 mt-0.5">{exam.id}</p>
                                </td>
                                <td className="p-4 text-sm font-medium text-gray-400">{exam.org}</td>
                                <td className="p-4 text-center text-sm font-black text-emerald-400">{exam.candidates}</td>
                                <td className="p-4 text-center text-sm font-black text-amber-500">{exam.flags}</td>
                                <td className="p-4 pr-6 text-right">
                                    <button className="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg text-xs font-bold transition-colors shadow-sm">
                                        Suspend Global Execution
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                 </table>
            </div>
        </div>
    )
}

const GlobalAccounts = ({ users, organizations, loading, error, onRefresh, onEditUser, onDeleteUser }) => {
    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-white">Global Accounts</h1>
                    <p className="text-gray-400 font-medium mt-1">All platform users across candidates and organization admins.</p>
                </div>
                <button
                    onClick={onRefresh}
                    disabled={loading}
                    className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-gray-700 text-sm font-bold text-gray-200 hover:bg-gray-800 disabled:opacity-60"
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                </button>
            </div>

            <div className="bg-[#111] rounded-2xl border border-gray-800 overflow-hidden flex flex-col">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse min-w-[900px]">
                        <thead>
                            <tr className="bg-[#1a1a1a] border-b border-gray-800 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                <th className="p-4 pl-6">User</th>
                                <th className="p-4">Role</th>
                                <th className="p-4">Organization / Candidate</th>
                                <th className="p-4">Status</th>
                                <th className="p-4">Created</th>
                                <th className="p-4 pr-6 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800">
                            {loading && (
                                <tr>
                                    <td colSpan={6} className="p-8 text-center text-sm text-gray-500">Loading users...</td>
                                </tr>
                            )}

                            {!loading && error && (
                                <tr>
                                    <td colSpan={6} className="p-8 text-center text-sm text-red-400">{error}</td>
                                </tr>
                            )}

                            {!loading && !error && users.length === 0 && (
                                <tr>
                                    <td colSpan={6} className="p-8 text-center text-sm text-gray-500">No users found.</td>
                                </tr>
                            )}

                            {!loading && !error && users.map((item) => (
                                <tr key={item.id} className="hover:bg-gray-900 transition-colors">
                                    <td className="p-4 pl-6">
                                        <p className="font-bold text-sm text-white">{item.email}</p>
                                        <p className="text-xs font-mono text-gray-500 mt-0.5">USER-{String(item.id).padStart(4, '0')}</p>
                                    </td>
                                    <td className="p-4">
                                        <span className="inline-flex px-2.5 py-1 rounded border border-gray-700 bg-gray-900 text-xs font-bold text-gray-300 uppercase">{item.role}</span>
                                    </td>
                                    <td className="p-4 text-sm text-gray-400 font-medium">
                                        {item.organizationNames?.length
                                            ? item.organizationNames.join(', ')
                                            : (item.organizationName || item.candidateName || '-')}
                                    </td>
                                    <td className="p-4">
                                        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-bold ${item.active ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                                            {item.active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td className="p-4 text-sm font-medium text-gray-500">{item.created}</td>
                                    <td className="p-4 pr-6 text-right">
                                        <button
                                            onClick={() => onEditUser(item)}
                                            className="p-2 text-gray-500 hover:text-indigo-400 hover:bg-gray-800 rounded-lg transition-colors"
                                        >
                                            <Edit2 className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={() => onDeleteUser(item)}
                                            className="p-2 text-gray-500 hover:text-red-400 hover:bg-gray-800 rounded-lg transition-colors"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* <div className="bg-[#111] rounded-2xl border border-gray-800 flex-1 overflow-hidden flex flex-col">
                <div className="px-6 py-4 border-b border-gray-800 bg-[#1a1a1a]">
                    <h3 className="text-sm font-bold text-white">All Organizations</h3>
                    <p className="text-xs text-gray-500 mt-1">Includes active and inactive organizations.</p>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse min-w-[800px]">
                        <thead>
                            <tr className="bg-[#1a1a1a] border-b border-gray-800 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                <th className="p-4 pl-6">Organization</th>
                                <th className="p-4">Type</th>
                                <th className="p-4">Primary Contact</th>
                                <th className="p-4">Status</th>
                                <th className="p-4">Created</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800">
                            {organizations.length === 0 && (
                                <tr>
                                    <td colSpan={5} className="p-8 text-center text-sm text-gray-500">No organizations found.</td>
                                </tr>
                            )}

                            {organizations.map((org) => (
                                <tr key={org.id} className="hover:bg-gray-900 transition-colors">
                                    <td className="p-4 pl-6">
                                        <p className="font-bold text-sm text-white">{org.name}</p>
                                        <p className="text-xs font-mono text-gray-500 mt-0.5">{org.id}</p>
                                    </td>
                                    <td className="p-4 text-sm text-gray-300">{org.type || '-'}</td>
                                    <td className="p-4 text-sm text-gray-400">{org.email || '-'}</td>
                                    <td className="p-4">
                                        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-bold ${org.active ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                                            {org.active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td className="p-4 text-sm text-gray-500">{org.created}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div> */}
        </div>
    );
};

// --- Main Super Admin Dashboard Layout ---
const SuperAdminDashboard = () => {
    const navigate = useNavigate();
    const [activeView, setActiveView] = useState('dashboard');
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [organizations, setOrganizations] = useState([]);
    const [loadingOrganizations, setLoadingOrganizations] = useState(false);
    const [orgError, setOrgError] = useState('');
    const [users, setUsers] = useState([]);
    const [loadingUsers, setLoadingUsers] = useState(false);
    const [usersError, setUsersError] = useState('');
    const [showRegisterModal, setShowRegisterModal] = useState(false);
    const [registeringOrg, setRegisteringOrg] = useState(false);
    const [newOrg, setNewOrg] = useState({
        organization_name: '',
        organization_type: 'Company',
        primary_email: '',
        password: '',
    });
    const [toast, setToast] = useState({ type: '', message: '' });

    const [isSearchOpen, setIsSearchOpen] = useState(false);
    const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
    const headerRef = useRef(null);

    const superadminToken = localStorage.getItem('superadmin_token') || '';

    const pushToast = (type, message) => {
        setToast({ type, message });
        setTimeout(() => {
            setToast((prev) => (prev.message === message ? { type: '', message: '' } : prev));
        }, 3000);
    };

    const fetchOrganizations = useCallback(async () => {
        if (!superadminToken) {
            return;
        }

        setLoadingOrganizations(true);
        setOrgError('');

        try {
            const res = await fetch(`${API_BASE_URL}/auth/superadmin/organizations`, {
                headers: {
                    Authorization: `Bearer ${superadminToken}`,
                },
            });
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to load organizations');
            }

            const normalized = (data.organizations || []).map((org) => ({
                vendorId: org.vendor_id,
                id: `ORG-${String(org.vendor_id).padStart(3, '0')}`,
                name: org.organization_name || 'Unknown Organization',
                type: org.organization_type || 'Not specified',
                email: org.primary_email || '',
                active: String(org.status || '').toLowerCase() === 'active',
                status: org.status || 'Active',
                created: org.created_at ? new Date(org.created_at).toLocaleDateString() : '-',
            }));
            setOrganizations(normalized);
        } catch (error) {
            setOrgError(error.message || 'Unable to load organizations.');
        } finally {
            setLoadingOrganizations(false);
        }
    }, [superadminToken]);

    const fetchUsers = useCallback(async () => {
        if (!superadminToken) {
            return;
        }

        setLoadingUsers(true);
        setUsersError('');

        try {
            const res = await fetch(`${API_BASE_URL}/auth/superadmin/users`, {
                headers: {
                    Authorization: `Bearer ${superadminToken}`,
                },
            });
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to load users');
            }

            const normalizedUsers = (data.users || []).map((item) => ({
                id: item.user_id,
                email: item.email || '-',
                role: item.role || 'unknown',
                active: !!item.is_active,
                organizationName: item.organization_name || '',
                organizationNames: item.organization_names || [],
                candidateName: item.candidate_name || '',
                created: item.created_at ? new Date(item.created_at).toLocaleDateString() : '-',
            }));

            setUsers(normalizedUsers);
        } catch (error) {
            setUsersError(error.message || 'Unable to load users.');
        } finally {
            setLoadingUsers(false);
        }
    }, [superadminToken]);

    const handleRegisterOrganization = async (e) => {
        e.preventDefault();
        setRegisteringOrg(true);

        try {
            const res = await fetch(`${API_BASE_URL}/auth/superadmin/register-organization`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${superadminToken}`,
                },
                body: JSON.stringify(newOrg),
            });
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to register organization');
            }

            setShowRegisterModal(false);
            setNewOrg({
                organization_name: '',
                organization_type: 'Company',
                primary_email: '',
                password: '',
            });
            pushToast('success', 'Organization registered successfully.');
            fetchOrganizations();
        } catch (error) {
            pushToast('error', error.message || 'Failed to register organization.');
        } finally {
            setRegisteringOrg(false);
        }
    };

    const handleEditUser = async (user) => {
        const nextEmail = window.prompt('Edit user email', user.email || '');
        if (nextEmail === null) {
            return;
        }

        const nextRole = window.prompt('Edit role (admin or candidate)', user.role || 'candidate');
        if (nextRole === null) {
            return;
        }

        const nextActiveRaw = window.prompt('Is active? (yes/no)', user.active ? 'yes' : 'no');
        if (nextActiveRaw === null) {
            return;
        }

        const payload = {};
        const normalizedEmail = nextEmail.trim().toLowerCase();
        const normalizedRole = nextRole.trim().toLowerCase();
        const normalizedActive = nextActiveRaw.trim().toLowerCase();

        if (normalizedEmail && normalizedEmail !== user.email) {
            payload.email = normalizedEmail;
        }
        if (normalizedRole && normalizedRole !== user.role) {
            payload.role = normalizedRole;
        }
        if (normalizedActive === 'yes' || normalizedActive === 'no') {
            const activeValue = normalizedActive === 'yes';
            if (activeValue !== user.active) {
                payload.is_active = activeValue;
            }
        }

        if (Object.keys(payload).length === 0) {
            pushToast('success', 'No user changes detected.');
            return;
        }

        try {
            const res = await fetch(`${API_BASE_URL}/auth/superadmin/users/${user.id}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${superadminToken}`,
                },
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to update user');
            }

            pushToast('success', 'User updated successfully.');
            fetchUsers();
            fetchOrganizations();
        } catch (error) {
            pushToast('error', error.message || 'Failed to update user.');
        }
    };

    const handleDeleteUser = async (user) => {
        const confirmed = window.confirm(`Delete user ${user.email}?`);
        if (!confirmed) {
            return;
        }

        try {
            const res = await fetch(`${API_BASE_URL}/auth/superadmin/users/${user.id}`, {
                method: 'DELETE',
                headers: {
                    Authorization: `Bearer ${superadminToken}`,
                },
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to delete user');
            }

            pushToast('success', 'User deleted successfully.');
            fetchUsers();
            fetchOrganizations();
        } catch (error) {
            pushToast('error', error.message || 'Failed to delete user.');
        }
    };

    const handleEditOrganization = async (org) => {
        const nextName = window.prompt('Edit organization name', org.name || '');
        if (nextName === null) {
            return;
        }

        const nextType = window.prompt('Edit organization type', org.type || 'Company');
        if (nextType === null) {
            return;
        }

        const nextEmail = window.prompt('Edit primary admin email', org.email || '');
        if (nextEmail === null) {
            return;
        }

        const nextActiveRaw = window.prompt('Organization status (active/inactive)', org.active ? 'active' : 'inactive');
        if (nextActiveRaw === null) {
            return;
        }

        const payload = {};
        if (nextName.trim() && nextName.trim() !== org.name) {
            payload.organization_name = nextName.trim();
        }
        if (nextType.trim() && nextType.trim() !== org.type) {
            payload.organization_type = nextType.trim();
        }
        const normalizedEmail = nextEmail.trim().toLowerCase();
        if (normalizedEmail && normalizedEmail !== (org.email || '').trim().toLowerCase()) {
            payload.primary_email = normalizedEmail;
        }
        const normalizedStatus = nextActiveRaw.trim().toLowerCase();
        if (normalizedStatus === 'active' || normalizedStatus === 'inactive') {
            const nextActive = normalizedStatus === 'active';
            if (nextActive !== !!org.active) {
                payload.is_active = nextActive;
            }
        }

        if (Object.keys(payload).length === 0) {
            pushToast('success', 'No organization changes detected.');
            return;
        }

        try {
            const res = await fetch(`${API_BASE_URL}/auth/superadmin/organizations/${org.vendorId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${superadminToken}`,
                },
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to update organization');
            }

            pushToast('success', 'Organization updated successfully.');
            fetchOrganizations();
            fetchUsers();
        } catch (error) {
            pushToast('error', error.message || 'Failed to update organization.');
        }
    };

    const handleDeleteOrganization = async (org) => {
        const confirmed = window.confirm(`Delete organization ${org.name}? This will permanently remove the organization and its admin user.`);
        if (!confirmed) {
            return;
        }

        try {
            const res = await fetch(`${API_BASE_URL}/auth/superadmin/organizations/${org.vendorId}`, {
                method: 'DELETE',
                headers: {
                    Authorization: `Bearer ${superadminToken}`,
                },
            });
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data?.detail || 'Failed to delete organization');
            }

            pushToast('success', 'Organization deleted successfully.');
            fetchOrganizations();
            fetchUsers();
        } catch (error) {
            pushToast('error', error.message || 'Failed to delete organization.');
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('superadmin_token');
        localStorage.removeItem('superadmin_email');
        navigate('/superadmin/login');
    };

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (headerRef.current && !headerRef.current.contains(event.target)) {
                setIsSearchOpen(false);
                setIsNotificationsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    useEffect(() => {
        if (!superadminToken) {
            navigate('/superadmin/login');
            return;
        }

        fetchOrganizations();
        fetchUsers();
    }, [superadminToken, navigate, fetchOrganizations, fetchUsers]);

    const navGroups = [
        {
            label: "Global Status",
            items: [
                { id: 'dashboard', label: 'Platform Overview', icon: LayoutDashboard },
                { id: 'analytics', label: 'Platform Analytics', icon: Activity },
            ]
        },
        {
            label: "Tenant Management",
            items: [
                { id: 'orgs', label: 'Organization Management', icon: Building2 },
                { id: 'admins', label: 'Admin Root Control', icon: UserCog },
                { id: 'users', label: 'Global Accounts', icon: Users },
                { id: 'monitoring', label: 'Global Monitoring', icon: MonitorPlay },
            ]
        },
        {
            label: "System Configuration",
            items: [
                { id: 'billing', label: 'Licensing & Billing', icon: CreditCard },
                { id: 'config', label: 'Core Configuration', icon: Settings },
                { id: 'security', label: 'Security & Audit', icon: ShieldAlert },
                { id: 'content', label: 'Content Policies', icon: FileText },
            ]
        },
        {
            label: "Operations",
            items: [
                { id: 'notifications', label: 'Global Broadcasts', icon: BellRing },
                { id: 'support', label: 'Issue Routing', icon: Ticket },
            ]
        }
    ];

    const renderView = () => {
        if (activeView === 'dashboard') return <GlobalDashboard />;
        if (activeView === 'orgs') {
            return (
                <OrgManagement
                    organizations={organizations}
                    loading={loadingOrganizations}
                    error={orgError}
                    onOpenRegister={() => setShowRegisterModal(true)}
                    onEditOrganization={handleEditOrganization}
                    onDeleteOrganization={handleDeleteOrganization}
                />
            );
        }
        if (activeView === 'users') {
            return (
                <GlobalAccounts
                    users={users}
                    organizations={organizations}
                    loading={loadingUsers}
                    error={usersError}
                    onRefresh={() => {
                        fetchUsers();
                        fetchOrganizations();
                    }}
                    onEditUser={handleEditUser}
                    onDeleteUser={handleDeleteUser}
                />
            );
        }
        if (activeView === 'monitoring') return <GlobalMonitoring />;
        
        // Return placeholders for remaining views for speed of development
        const viewData = [...navGroups.flatMap(g => g.items)].find(v => v.id === activeView);
        return <PlaceholderView title={viewData?.label} icon={viewData?.icon || LayoutDashboard} />;
    };

    return (
        <div className="min-h-screen bg-[#050505] flex font-sans selection:bg-indigo-500/30 text-gray-300">
            {/* Dark Sidebar */}
            <aside className={`fixed inset-y-0 left-0 z-40 w-72 bg-[#0a0a0a] border-r border-gray-800 flex flex-col transition-transform duration-300 ease-in-out md:translate-x-0 md:static ${isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"}`}>
                <div className="h-20 flex items-center px-6 border-b border-gray-800 bg-[#0a0a0a]">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-xl bg-gray-900 flex items-center justify-center border border-gray-700 shadow-[0_0_15px_rgba(255,255,255,0.05)] relative overflow-hidden">
                             <div className="absolute inset-0 bg-indigo-500/20 blur-xl"></div>
                             <ShieldAlert className="w-5 h-5 text-indigo-400 relative z-10" />
                        </div>
                        <span className="text-xl font-black text-white tracking-tight">System Root</span>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-8 scrollbar-hide">
                    {navGroups.map((group, idx) => (
                        <div key={idx} className="space-y-1">
                            <h3 className="px-4 text-[10px] font-black tracking-widest text-gray-600 uppercase mb-3">
                                {group.label}
                            </h3>
                            {group.items.map((item) => (
                                <button
                                    key={item.id}
                                    onClick={() => { setActiveView(item.id); setIsMobileMenuOpen(false); }}
                                    className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl font-medium text-sm transition-all focus:outline-none ${
                                        activeView === item.id 
                                        ? 'bg-indigo-500/10 text-indigo-400 shadow-[inset_2px_0_0_var(--tw-colors-indigo-500)]' 
                                        : 'text-gray-500 hover:bg-gray-900 hover:text-gray-300'
                                    }`}
                                >
                                    <item.icon className="w-5 h-5" />
                                    {item.label}
                                </button>
                            ))}
                        </div>
                    ))}
                </div>

                <div className="p-4 border-t border-gray-800 bg-[#0a0a0a]">
                    <button onClick={handleLogout} className="w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm text-red-400 hover:bg-red-500/10 transition-colors">
                        <LogOut className="w-5 h-5" />
                        Terminate Session
                    </button>
                </div>
            </aside>

            {toast.message && (
                <div className={`fixed right-6 top-6 z-[100] rounded-xl border px-4 py-3 text-sm font-semibold shadow-2xl ${toast.type === 'success' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-red-500/30 bg-red-500/10 text-red-300'}`}>
                    {toast.message}
                </div>
            )}

            {/* Mobile overlay */}
            {isMobileMenuOpen && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-30 md:hidden" onClick={() => setIsMobileMenuOpen(false)}></div>
            )}

            {/* Main Content Area */}
            <main className="flex-1 h-[100dvh] overflow-y-auto relative bg-[#050505] scrollbar-hide">
                {/* Header Context Bar */}
                <header ref={headerRef} className="sticky top-0 z-30 bg-[#0a0a0a]/80 backdrop-blur-xl border-b border-gray-800 px-6 md:px-10 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3 w-1/4">
                        <div className="w-8 h-8 rounded-full bg-gray-900 border border-gray-700 flex items-center justify-center">
                            <Lock className="w-4 h-4 text-emerald-400" />
                        </div>
                        <div className="hidden sm:block">
                            <h2 className="text-sm font-bold text-white leading-tight">Root User</h2>
                            <p className="text-xs font-medium text-emerald-400 leading-tight flex items-center gap-1">Secured Connect <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span></p>
                        </div>
                    </div>

                    {/* Central Search */}
                    <div className="flex-1 max-w-xl hidden md:block relative">
                        <div className="relative group cursor-text" onClick={() => setIsSearchOpen(true)}>
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 group-hover:text-indigo-400 transition-colors" />
                            <div className="w-full pl-10 pr-4 py-2 bg-[#111] border border-gray-800 rounded-xl flex items-center justify-between transition-all font-medium text-sm text-gray-500 group-hover:bg-[#1a1a1a]">
                                <span>Global System Search...</span>
                                <div className="flex gap-1">
                                    <kbd className="hidden lg:inline-flex items-center px-1.5 py-0.5 border border-gray-700 rounded text-xs font-mono font-bold text-gray-500 bg-gray-900">Ctrl</kbd>
                                    <kbd className="hidden lg:inline-flex items-center px-1.5 py-0.5 border border-gray-700 rounded text-xs font-mono font-bold text-gray-500 bg-gray-900">K</kbd>
                                </div>
                            </div>
                        </div>

                        <AnimatePresence>
                            {isSearchOpen && (
                                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }} className="absolute top-full left-0 right-0 mt-2 bg-[#111] rounded-2xl shadow-[0_0_40px_rgba(0,0,0,0.8)] border border-gray-800 overflow-hidden z-50 origin-top">
                                    <div className="p-3 border-b border-gray-800 flex items-center gap-3 bg-[#1a1a1a]">
                                        <Search className="w-5 h-5 text-indigo-400 shrink-0" />
                                        <input autoFocus type="text" placeholder="Search orgs, users, exams..." className="w-full bg-transparent border-none outline-none font-medium text-white placeholder:text-gray-600" />
                                        <button onClick={() => setIsSearchOpen(false)} className="p-1 rounded bg-gray-900 text-gray-500 hover:text-white transition-colors text-xs font-bold uppercase border border-gray-800">Esc</button>
                                    </div>
                                    <div className="p-4 text-center text-gray-500 text-sm font-medium">Type at least 3 characters.</div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    <div className="flex items-center justify-end gap-3 w-1/4">
                        <button onClick={() => setIsNotificationsOpen(!isNotificationsOpen)} className="hidden sm:flex relative p-2 text-gray-500 hover:text-white bg-[#111] border border-gray-800 rounded-xl transition-colors">
                            <BellRing className="w-5 h-5" />
                            <span className="absolute top-0 right-0 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-[#111]"></span>
                        </button>
                        
                        <AnimatePresence>
                            {isNotificationsOpen && (
                                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }} className="absolute top-[calc(100%+12px)] right-6 w-80 bg-[#111] rounded-2xl shadow-2xl border border-gray-800 overflow-hidden z-50 origin-top-right">
                                    <div className="p-4 border-b border-gray-800 flex justify-between bg-[#1a1a1a]">
                                        <h3 className="font-bold text-white">System Alerts</h3>
                                        <button className="text-xs font-bold text-indigo-400">Clear</button>
                                    </div>
                                    <div className="p-4 text-center text-sm font-medium text-gray-500">No new critical alerts.</div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <button className="md:hidden p-2 text-gray-400" onClick={() => setIsMobileMenuOpen(true)}>
                            <Menu className="w-6 h-6" />
                        </button>
                    </div>
                </header>

                {/* View Content Container */}
                <div className="p-6 md:p-10 max-w-[1600px] mx-auto min-h-[calc(100vh-80px)]">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={activeView}
                            initial={{ opacity: 0, scale: 0.98, filter: "blur(4px)" }}
                            animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                            exit={{ opacity: 0, scale: 1.02, filter: "blur(4px)" }}
                            transition={{ duration: 0.2 }}
                            className="h-full"
                        >
                            {renderView()}
                        </motion.div>
                    </AnimatePresence>
                </div>
            </main>

            <AnimatePresence>
                {showRegisterModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[90] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
                        onClick={() => setShowRegisterModal(false)}
                    >
                        <motion.div
                            initial={{ opacity: 0, y: 20, scale: 0.98 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: 10, scale: 0.98 }}
                            className="w-full max-w-xl bg-[#111] border border-gray-800 rounded-2xl p-6"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <h2 className="text-xl font-bold text-white">Register Organization</h2>
                            <p className="mt-1 text-sm text-gray-400">Create organization and primary admin credentials.</p>

                            <form onSubmit={handleRegisterOrganization} className="mt-6 space-y-4">
                                <input
                                    type="text"
                                    required
                                    value={newOrg.organization_name}
                                    onChange={(e) => setNewOrg((prev) => ({ ...prev, organization_name: e.target.value }))}
                                    placeholder="Organization Name"
                                    className="w-full rounded-xl border border-gray-800 bg-[#0a0a0a] px-4 py-3 text-sm text-white outline-none focus:border-indigo-500"
                                />

                                <select
                                    value={newOrg.organization_type}
                                    onChange={(e) => setNewOrg((prev) => ({ ...prev, organization_type: e.target.value }))}
                                    className="w-full rounded-xl border border-gray-800 bg-[#0a0a0a] px-4 py-3 text-sm text-white outline-none focus:border-indigo-500"
                                >
                                    <option>Company</option>
                                    <option>University</option>
                                    <option>Certification</option>
                                    <option>Training Institute</option>
                                </select>

                                <input
                                    type="email"
                                    required
                                    value={newOrg.primary_email}
                                    onChange={(e) => setNewOrg((prev) => ({ ...prev, primary_email: e.target.value }))}
                                    placeholder="Primary Admin Email"
                                    className="w-full rounded-xl border border-gray-800 bg-[#0a0a0a] px-4 py-3 text-sm text-white outline-none focus:border-indigo-500"
                                />

                                <input
                                    type="password"
                                    required
                                    minLength={6}
                                    value={newOrg.password}
                                    onChange={(e) => setNewOrg((prev) => ({ ...prev, password: e.target.value }))}
                                    placeholder="Primary Admin Password"
                                    className="w-full rounded-xl border border-gray-800 bg-[#0a0a0a] px-4 py-3 text-sm text-white outline-none focus:border-indigo-500"
                                />

                                <div className="flex items-center justify-end gap-3 pt-2">
                                    <button
                                        type="button"
                                        onClick={() => setShowRegisterModal(false)}
                                        className="rounded-xl border border-gray-700 px-4 py-2 text-sm font-semibold text-gray-300 hover:bg-gray-800"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={registeringOrg}
                                        className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
                                    >
                                        {registeringOrg ? 'Creating...' : 'Create Organization'}
                                    </button>
                                </div>
                            </form>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default SuperAdminDashboard;

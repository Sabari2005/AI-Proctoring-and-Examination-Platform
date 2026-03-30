import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, Lock, Mail } from 'lucide-react';
import { BACKEND_URL } from '../contexts/BackendContext';

const API_BASE_URL = BACKEND_URL;

const SuperAdminLogin = () => {
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = useState(false);
    const [email, setEmail] = useState('root@observe.platform');
    const [password, setPassword] = useState('');
    const [statusMessage, setStatusMessage] = useState('');
    const [statusType, setStatusType] = useState('error');

    const handleLogin = async (e) => {
        e.preventDefault();
        setStatusMessage('');
        setIsLoading(true);

        try {
            const res = await fetch(`${API_BASE_URL}/auth/superadmin/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email.trim(), password }),
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data?.detail || 'Superadmin login failed');
            }

            localStorage.setItem('superadmin_token', data.access_token || '');
            localStorage.setItem('superadmin_email', data.email || email.trim());
            setStatusType('success');
            setStatusMessage('Login successful. Redirecting...');
            navigate('/superadmin/dashboard');
        } catch (error) {
            setStatusType('error');
            setStatusMessage(error.message || 'Unable to login right now.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center p-4 relative overflow-hidden">
            {/* Dark background effects */}
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/20 via-[#0a0a0a] to-[#0a0a0a]"></div>
            <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-[120px]"></div>

            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="w-full max-w-md relative z-10"
            >
                {/* Header Sequence */}
                <div className="flex flex-col items-center mb-8">
                    <div className="w-16 h-16 bg-gray-900 border border-gray-800 rounded-2xl flex items-center justify-center mb-6 shadow-2xl relative">
                        <div className="absolute inset-0 bg-indigo-500/20 rounded-2xl blur-xl"></div>
                        <ShieldAlert className="w-8 h-8 text-indigo-400 relative z-10" />
                    </div>
                    <h1 className="text-3xl font-black text-white tracking-tight">Super Admin Portal</h1>
                    <p className="text-gray-400 font-medium tracking-wide text-sm mt-2 uppercase">Restricted Access Area</p>
                </div>

                {/* Login Card */}
                <div className="bg-gray-900/50 backdrop-blur-xl border border-gray-800 p-8 rounded-[2rem] shadow-2xl">
                    <form onSubmit={handleLogin} className="space-y-6">
                        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
                            <div>
                                <label className="block text-sm font-bold text-gray-400 mb-2 uppercase tracking-wide">Root Email Address</label>
                                <div className="relative">
                                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                                    <input
                                        type="email"
                                        required
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full pl-12 pr-4 py-3 bg-[#0a0a0a] border border-gray-800 text-white rounded-xl focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 outline-none transition-all font-medium placeholder:text-gray-600 shadow-inner"
                                        placeholder="sysadmin@company.com"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-gray-400 mb-2 uppercase tracking-wide">Master Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                                    <input
                                        type="password"
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="w-full pl-12 pr-4 py-3 bg-[#0a0a0a] border border-gray-800 text-white rounded-xl focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 outline-none transition-all font-medium placeholder:text-gray-600 shadow-inner"
                                        placeholder="••••••••••••"
                                    />
                                </div>
                            </div>
                        </motion.div>

                        {statusMessage && (
                            <div className={`rounded-xl border px-4 py-3 text-sm font-medium ${statusType === 'success' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-red-500/30 bg-red-500/10 text-red-300'}`}>
                                {statusMessage}
                            </div>
                        )}

                        <button 
                            type="submit" 
                            disabled={isLoading}
                            className="w-full py-3.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold flex items-center justify-center transition-all duration-300 disabled:opacity-50 shadow-[0_0_20px_rgba(79,70,229,0.3)] disabled:shadow-none"
                        >
                            {isLoading ? (
                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                            ) : (
                                'Authenticate'
                            )}
                        </button>
                    </form>
                </div>
                
                {/* Footer warning */}
                <div className="mt-8 text-center px-6">
                    <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest leading-relaxed">
                        Unauthorized access is strictly prohibited and monitored.<br/>
                        All actions are logged securely.
                    </p>
                </div>
            </motion.div>
        </div>
    );
};

export default SuperAdminLogin;

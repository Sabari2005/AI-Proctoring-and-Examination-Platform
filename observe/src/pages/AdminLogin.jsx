import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { BACKEND_URL } from '../contexts/BackendContext';

const API_BASE_URL = BACKEND_URL;

const AdminLogin = () => {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            const res = await fetch(`${API_BASE_URL}/auth/admin/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email.trim(), password }),
            });

            const data = await res.json();
            if (!res.ok) {
                throw new Error(data?.detail || 'Admin login failed');
            }

            localStorage.setItem('admin_token', data.access_token || '');
            localStorage.setItem('admin_vendor_id', String(data.vendor_id || ''));
            localStorage.setItem('admin_email', data.email || email.trim());
            navigate('/admin/dashboard');
        } catch (err) {
            setError(err.message || 'Unable to login right now.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center text-center px-6 relative overflow-hidden">
            {/* Minimal Background Decor */}
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-gray-900 via-indigo-600 to-gray-900"></div>

            <a href="/" className="absolute top-8 left-8 flex items-center gap-2 group cursor-pointer z-10 hover:opacity-75 transition-opacity">
                <div className="w-8 h-8 bg-black text-white rounded-lg flex items-center justify-center font-bold text-lg">
                    O
                </div>
                <span className="text-xl font-bold tracking-tight text-black">
                    Observe.
                </span>
            </a>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="w-full max-w-md bg-white p-10 rounded-3xl border border-gray-200 shadow-2xl shadow-gray-200/50 relative z-10"
            >
                <div className="w-16 h-16 bg-gray-900 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-inner">
                    <ShieldCheck className="w-8 h-8 text-white" />
                </div>
                <h1 className="text-2xl font-bold tracking-tight text-gray-900 mb-2">Admin Portal</h1>
                <p className="text-gray-500 font-medium text-sm mb-8">Sign in with organization credentials to manage exams and candidates.</p>

                <form className="flex flex-col gap-4 text-left" onSubmit={handleLogin}>
                    <div>
                        <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest mb-2 ml-1">Admin Email</label>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full px-4 py-3 bg-gray-50 rounded-xl border border-gray-200 focus:outline-none focus:bg-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-medium text-gray-900"
                        />
                    </div>
                    <div>
                        <div className="flex items-center justify-between mb-2 ml-1">
                            <label className="block text-xs font-bold text-gray-700 uppercase tracking-widest">Password</label>
                            <a href="#" className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition-colors">Recover</a>
                        </div>
                        <input
                            type="password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full px-4 py-3 bg-gray-50 rounded-xl border border-gray-200 focus:outline-none focus:bg-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-medium text-gray-900"
                        />
                    </div>

                    {error && (
                        <p className="text-sm font-medium text-red-500">{error}</p>
                    )}

                    <button type="submit" disabled={isLoading} className="w-full px-4 py-3 rounded-xl bg-gray-900 text-white font-bold text-sm hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 shadow-md hover:shadow-lg mt-4 flex items-center justify-center gap-2 group disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-y-0">
                        {isLoading ? 'Authenticating...' : 'Authenticate'} <ShieldCheck className="w-4 h-4 opacity-50 group-hover:opacity-100 transition-opacity" />
                    </button>
                </form>

                <div className="mt-8 pt-6 border-t border-gray-100">
                    <p className="text-xs font-medium text-gray-400">
                        Unauthorized access is strictly prohibited. All actions are logged and audited.
                    </p>
                </div>
            </motion.div>
        </div>
    );
};

export default AdminLogin;

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, BookOpen, Terminal, Code, FileText, ChevronRight, Hash } from 'lucide-react';

const Docs = () => {
    const [activeSection, setActiveSection] = useState('getting-started');

    const sections = [
        { id: 'getting-started', label: 'Getting Started', icon: BookOpen },
        { id: 'authentication', label: 'Authentication', icon: Terminal },
        { id: 'api-reference', label: 'API Reference', icon: Code },
        { id: 'webhooks', label: 'Webhooks', icon: Hash },
        { id: 'guides', label: 'Integration Guides', icon: FileText },
    ];

    return (
        <div className="min-h-screen bg-[#F8FAFC] pb-20 pt-28">
            <div className="max-w-[1400px] mx-auto px-6 h-full flex flex-col md:flex-row gap-8">
                
                {/* Sidebar */}
                <aside className="w-full md:w-64 shrink-0 flex flex-col gap-6 sticky top-28 h-[calc(100vh-120px)] overflow-y-auto scrollbar-hide">
                    <div>
                        <div className="relative mb-6">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                            <input type="text" placeholder="Search docs..." className="w-full pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 outline-none text-sm transition-all shadow-sm" />
                        </div>
                        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3 px-2">Documentation</h3>
                        <nav className="space-y-1">
                            {sections.map(s => (
                                <button key={s.id} onClick={() => setActiveSection(s.id)} className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${activeSection === s.id ? 'bg-indigo-50 text-indigo-700 font-bold' : 'text-gray-600 hover:bg-white hover:text-gray-900 font-medium'}`}>
                                    <div className="flex items-center gap-2">
                                        <s.icon className={`w-4 h-4 ${activeSection === s.id ? 'text-indigo-600' : 'text-gray-400'}`} />
                                        {s.label}
                                    </div>
                                    {activeSection === s.id && <ChevronRight className="w-4 h-4" />}
                                </button>
                            ))}
                        </nav>
                    </div>
                </aside>

                {/* Main Content Areas */}
                <main className="flex-1 bg-white rounded-3xl p-8 md:p-12 shadow-sm border border-gray-100 min-h-[600px]">
                    <motion.div
                        key={activeSection}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3 }}
                    >
                        {activeSection === 'getting-started' && (
                            <div className="space-y-6 max-w-3xl">
                                <h1 className="text-3xl md:text-5xl font-bold text-gray-900 tracking-tight mb-4">Getting Started</h1>
                                <p className="text-lg text-gray-600 leading-relaxed">Welcome to the Observe Platform documentation. Here you'll find everything you need to know about integrating our proctoring engine into your existing workflows, LMS, or ATS.</p>
                                
                                <div className="grid sm:grid-cols-2 gap-4 mt-8">
                                    <div className="p-6 rounded-2xl border border-gray-200 hover:border-indigo-300 transition-colors cursor-pointer group">
                                        <div className="w-10 h-10 bg-indigo-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-indigo-100 transition-colors">
                                            <Code className="w-5 h-5 text-indigo-600" />
                                        </div>
                                        <h3 className="text-lg font-bold text-gray-900 mb-2">REST API Quickstart</h3>
                                        <p className="text-sm text-gray-500">Learn how to authenticate and make your first API request.</p>
                                    </div>
                                    <div className="p-6 rounded-2xl border border-gray-200 hover:border-indigo-300 transition-colors cursor-pointer group">
                                        <div className="w-10 h-10 bg-emerald-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-emerald-100 transition-colors">
                                            <Terminal className="w-5 h-5 text-emerald-600" />
                                        </div>
                                        <h3 className="text-lg font-bold text-gray-900 mb-2">Webhooks Guide</h3>
                                        <p className="text-sm text-gray-500">Subscribe to real-time events for candidate sessions and flags.</p>
                                    </div>
                                </div>

                                <div className="mt-12 space-y-4">
                                    <h2 className="text-2xl font-bold text-gray-900">Base URL</h2>
                                    <p className="text-gray-600">All API requests should be prefixed with the following base URL:</p>
                                    <div className="bg-gray-900 rounded-xl p-4 flex items-center justify-between group flex-wrap gap-2">
                                        <code className="text-emerald-400 font-mono text-sm">https://api.observe.app/v1</code>
                                        <button className="text-gray-400 hover:text-white transition-colors text-xs font-bold uppercase tracking-wider bg-gray-800 px-3 py-1.5 rounded-lg opacity-0 group-hover:opacity-100">Copy</button>
                                    </div>
                                </div>
                            </div>
                        )}
                        {/* Placeholder for other sections */}
                        {activeSection !== 'getting-started' && (
                            <div className="flex flex-col items-center justify-center py-20 text-center">
                                <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center mb-6">
                                    <Code className="w-8 h-8 text-indigo-500" />
                                </div>
                                <h2 className="text-2xl font-bold text-gray-900 mb-2">Under Construction</h2>
                                <p className="text-gray-500">Detailed docs for {sections.find(s=>s.id === activeSection)?.label} are coming soon.</p>
                            </div>
                        )}
                    </motion.div>
                </main>
            </div>
        </div>
    );
};

export default Docs;

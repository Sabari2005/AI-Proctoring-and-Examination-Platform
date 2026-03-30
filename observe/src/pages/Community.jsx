import React from 'react';
import { motion } from 'framer-motion';
import { MessageSquare, Users, Video, Github, ArrowRight } from 'lucide-react';

const Community = () => {
    return (
        <div className="min-h-screen bg-black text-white pb-20 pt-32 selection:bg-indigo-500/30">
            <div className="max-w-[1200px] mx-auto px-6">
                
                <div className="text-center max-w-3xl mx-auto mb-20">
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-white text-xs font-bold tracking-widest uppercase mb-6 border border-white/20 shadow-lg">
                        Join 10,000+ Educators & Engineers
                    </motion.div>
                    <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
                        Observe Community
                    </motion.h1>
                    <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="text-xl text-gray-400 leading-relaxed">
                        Connect with peers, share best practices, and help shape the future of digital assessments.
                    </motion.p>
                </div>

                <div className="grid md:grid-cols-2 gap-6 mb-20">
                    <div className="bg-white/5 border border-white/10 p-8 md:p-12 rounded-[2rem] hover:bg-white/10 transition-colors group cursor-pointer relative overflow-hidden shadow-2xl">
                        <div className="absolute -right-10 -top-10 w-40 h-40 bg-indigo-500 rounded-full blur-3xl opacity-20 group-hover:opacity-40 transition-opacity duration-500"></div>
                        <div className="w-14 h-14 bg-indigo-500/20 text-indigo-400 rounded-2xl flex items-center justify-center mb-8 border border-indigo-500/30">
                            <MessageSquare className="w-7 h-7" />
                        </div>
                        <h3 className="text-3xl font-bold mb-4">Discord Server</h3>
                        <p className="text-gray-400 text-lg mb-8 max-w-sm">Hop into our active Discord to chat directly with our engineering team and other platform admins.</p>
                        <button className="flex items-center justify-center w-full md:w-auto gap-2 text-white font-bold bg-white/10 px-6 py-3 rounded-xl hover:bg-white/20 transition-colors">
                            Join Discord <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
                        </button>
                    </div>

                    <div className="bg-white/5 border border-white/10 p-8 md:p-12 rounded-[2rem] hover:bg-white/10 transition-colors group cursor-pointer relative overflow-hidden shadow-2xl">
                        <div className="absolute -right-10 -top-10 w-40 h-40 bg-emerald-500 rounded-full blur-3xl opacity-20 group-hover:opacity-40 transition-opacity duration-500"></div>
                        <div className="w-14 h-14 bg-emerald-500/20 text-emerald-400 rounded-2xl flex items-center justify-center mb-8 border border-emerald-500/30">
                            <Video className="w-7 h-7" />
                        </div>
                        <h3 className="text-3xl font-bold mb-4">Webinars & Events</h3>
                        <p className="text-gray-400 text-lg mb-8 max-w-sm">Join our bi-weekly deep dives into platform configuration and advanced proctoring strategies.</p>
                        <button className="flex items-center justify-center w-full md:w-auto gap-2 text-white font-bold bg-white/10 px-6 py-3 rounded-xl hover:bg-white/20 transition-colors">
                            View Schedule <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
                        </button>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default Community;

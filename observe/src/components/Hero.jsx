import React from 'react';
import { motion } from 'framer-motion';
import { Shield, PlayCircle } from 'lucide-react';

const Hero = () => {
    return (
        <section className="relative pt-32 pb-20 md:pt-40 md:pb-28 px-6 lg:px-12 max-w-[1400px] mx-auto flex flex-col lg:flex-row items-center gap-12 lg:gap-20 overflow-hidden">

            {/* Left Content */}
            <div className="flex-1 z-10 w-full">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, ease: "easeOut" }}
                    className="inline-flex items-center gap-2 px-3 py-1.5 mb-8 rounded-full border border-gray-200 bg-gray-50 text-sm font-medium text-gray-700 shadow-sm"
                >
                    <Shield className="w-4 h-4 text-[#2A2B32]" />
                    <span>Next-Gen Enterprise Security</span>
                </motion.div>

                <motion.h1
                    className="text-5xl md:text-7xl lg:text-[80px] font-bold tracking-tight leading-[1.05] text-[#111827] mb-8"
                    initial={{ opacity: 0, y: 40 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.7, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
                >
                    Integrity,<br />
                    <span className="text-[#2A2B32]">Observed.</span>
                </motion.h1>

                <motion.p
                    className="text-lg md:text-xl text-gray-600 mb-10 max-w-xl font-medium leading-relaxed"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.7, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
                >
                    The AI-driven proctoring suite built to safeguard modern education and enterprise assessments without compromising the candidate experience.
                </motion.p>

                <motion.div
                    className="flex flex-col sm:flex-row items-start sm:items-center gap-4"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.7, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
                >
                    <button className="w-full sm:w-auto px-8 py-4 text-white bg-[#2A2B32] rounded-lg hover:bg-[#1f2025] transition-colors shadow-lg font-semibold text-lg flex items-center justify-center gap-2">
                        Start your free trial
                    </button>

                    <button className="w-full sm:w-auto px-8 py-4 text-gray-700 bg-white border-2 border-gray-200 rounded-lg hover:bg-gray-50 hover:border-gray-300 transition-all font-semibold text-lg flex items-center justify-center gap-2">
                        <PlayCircle className="w-5 h-5 text-gray-500" />
                        Watch video
                    </button>
                </motion.div>

                <motion.div
                    className="mt-10 flex items-center gap-4 text-sm text-gray-500 font-medium"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 1, delay: 0.6 }}
                >
                    <span>No credit card required</span>
                    <span className="w-1 h-1 rounded-full bg-gray-300"></span>
                    <span>14-day free trial</span>
                    <span className="w-1 h-1 rounded-full bg-gray-300"></span>
                    <span>Cancel anytime</span>
                </motion.div>
            </div>

            {/* Right Content / Graphic Area */}
            <motion.div
                className="flex-1 w-full relative"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.8, delay: 0.3, ease: "easeOut" }}
            >
                <div className="aspect-[4/3] w-full rounded-2xl bg-[#E5E7EB] border border-gray-200 shadow-2xl flex items-center justify-center relative overflow-hidden group p-1">

                    {/* Minimalist Dashboard UI Mockup */}
                    <div className="absolute inset-2 border border-gray-200 bg-white rounded-xl shadow-[0_10px_30px_rgba(0,0,0,0.05)] flex flex-col p-4 overflow-hidden">

                        {/* Dashboard Header UI */}
                        <div className="flex justify-between items-center border-b border-gray-100 pb-3 mb-4 shrink-0">
                            <div className="flex gap-2 items-center">
                                <div className="w-3 h-3 rounded-full bg-red-400"></div>
                                <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                                <div className="w-3 h-3 rounded-full bg-green-400"></div>
                            </div>

                            {/* Fake Search bar */}
                            <div className="flex-1 max-w-xs mx-4 h-7 bg-gray-50 border border-gray-100 rounded-md flex items-center px-2 gap-2">
                                <div className="w-3 h-3 border-2 border-gray-300 rounded-full"></div>
                                <div className="h-1.5 w-16 bg-gray-200 rounded-full"></div>
                            </div>

                            <div className="flex gap-3 items-center">
                                <div className="h-4 w-4 rounded-full bg-gray-200"></div>
                                <div className="h-7 w-7 bg-[#2A2B32] rounded-full ring-2 ring-gray-100 ring-offset-1"></div>
                            </div>
                        </div>

                        {/* Dashboard Main Content Area */}
                        <div className="flex-1 gap-5 w-full flex">

                            {/* Left Navigation / Sidebar */}
                            <div className="w-32 flex flex-col gap-2 border-r border-gray-100 pr-4 shrink-0">
                                <div className="h-6 w-full bg-gray-100 rounded-md mb-4 flex items-center px-2">
                                    <div className="h-2 w-12 bg-gray-300 rounded-full"></div>
                                </div>
                                <div className="h-6 w-full bg-gray-50 rounded-md flex items-center px-2 gap-2">
                                    <div className="h-2.5 w-2.5 bg-gray-200 rounded-sm"></div>
                                    <div className="h-1.5 w-14 bg-gray-200 rounded-full"></div>
                                </div>
                                <div className="h-6 w-full hover:bg-gray-50 rounded-md flex items-center px-2 gap-2 transition-colors">
                                    <div className="h-2.5 w-2.5 bg-gray-200 rounded-sm"></div>
                                    <div className="h-1.5 w-10 bg-gray-200 rounded-full"></div>
                                </div>
                                <div className="h-6 w-full hover:bg-gray-50 rounded-md flex items-center px-2 gap-2 transition-colors">
                                    <div className="h-2.5 w-2.5 bg-gray-200 rounded-sm"></div>
                                    <div className="h-1.5 w-16 bg-gray-200 rounded-full"></div>
                                </div>
                                <div className="mt-auto h-20 w-full bg-gray-50 rounded-lg border border-gray-100 flex flex-col items-center justify-center gap-2 p-2 relative overflow-hidden">
                                    <div className="h-1.5 w-16 bg-gray-200 rounded-full"></div>
                                    <div className="h-2 w-full bg-white rounded-full overflow-hidden content-start">
                                        <div className="h-full w-2/3 bg-blue-500 rounded-full"></div>
                                    </div>
                                    <div className="absolute top-0 right-0 -mr-4 -mt-4 w-12 h-12 bg-[#2A2B32]/10 rounded-full blur-xl"></div>
                                </div>
                            </div>

                            {/* Main Middle Content Area (Video Feed) */}
                            <div className="flex-1 flex flex-col gap-4">
                                {/* Video Player Mockup */}
                                <div className="flex-1 w-full bg-[#111827] rounded-xl flex items-center justify-center relative overflow-hidden shadow-inner group/video">

                                    <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-black/50 backdrop-blur-md px-2 py-1 rounded shadow-sm z-10 border border-white/10">
                                        <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-[pulse_1.5s_ease-in-out_infinite]"></div>
                                        <span className="text-[9px] text-white/90 font-bold uppercase tracking-widest">Live</span>
                                    </div>

                                    <div className="absolute top-3 right-3 bg-black/50 backdrop-blur-md px-2 py-1 rounded shadow-sm z-10 border border-white/10">
                                        <span className="text-[9px] text-white/90 font-mono tracking-widest">CAM-01</span>
                                    </div>

                                    {/* AI Scanning Visuals */}
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        {/* Face wireframe/reticle */}
                                        <div className="w-32 h-40 border border-green-500/30 rounded-[30%] relative">
                                            <div className="absolute top-1/4 left-1/4 w-3 h-3 border-t border-l border-green-500/50"></div>
                                            <div className="absolute top-1/4 right-1/4 w-3 h-3 border-t border-r border-green-500/50"></div>
                                            <div className="absolute bottom-1/4 left-1/4 w-3 h-3 border-b border-l border-green-500/50"></div>
                                            <div className="absolute bottom-1/4 right-1/4 w-3 h-3 border-b border-r border-green-500/50"></div>
                                            <div className="absolute top-1/2 left-0 w-full h-[1px] bg-green-500/20 shadow-[0_0_8px_rgba(34,197,94,0.3)] animate-[bounce_3s_infinite]"></div>
                                        </div>
                                    </div>

                                    {/* Bottom Player Controls */}
                                    <div className="absolute bottom-3 left-3 right-3 flex items-center gap-3">
                                        <div className="w-6 h-6 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center">
                                            <div className="w-2 h-2 bg-white rounded-sm"></div>
                                        </div>
                                        <div className="flex-1 h-1 bg-white/20 rounded-full flex items-center">
                                            <div className="w-1/3 h-full bg-white rounded-full"></div>
                                            <div className="w-2 h-2 rounded-full bg-white -ml-1"></div>
                                        </div>
                                        <div className="h-1.5 w-8 bg-white/40 rounded-full"></div>
                                    </div>
                                </div>

                                {/* Recent Activity Mini-cards */}
                                <div className="h-20 w-full flex gap-3 shrink-0">
                                    <div className="flex-1 bg-white border border-gray-200 rounded-lg shadow-sm p-3 flex flex-col justify-between relative overflow-hidden">
                                        <div className="h-1.5 w-10 bg-gray-200 rounded-full"></div>
                                        <div className="h-4 w-16 bg-red-100 rounded-md"></div>
                                        <div className="absolute bottom-0 right-0 p-2 opacity-10">
                                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="red" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                                        </div>
                                    </div>
                                    <div className="flex-1 bg-white border border-gray-200 rounded-lg shadow-sm p-3 flex flex-col justify-between">
                                        <div className="h-1.5 w-14 bg-gray-200 rounded-full"></div>
                                        <div className="h-4 w-20 bg-green-50 rounded-md"></div>
                                    </div>
                                </div>
                            </div>

                            {/* Right Details Panel */}
                            <div className="w-40 flex flex-col gap-4 border-l border-gray-100 pl-4 shrink-0">
                                {/* Profile Stub */}
                                <div className="flex items-center gap-3 w-full">
                                    <div className="h-10 w-10 rounded-full bg-gray-100 border border-gray-200"></div>
                                    <div className="flex flex-col gap-1.5">
                                        <div className="h-2 w-16 bg-gray-300 rounded-full"></div>
                                        <div className="h-1.5 w-10 bg-gray-200 rounded-full"></div>
                                    </div>
                                </div>

                                {/* Stats / Graphs */}
                                <div className="flex-1 flex flex-col gap-4 mt-2">
                                    <div className="w-full h-24 bg-gray-50 rounded-lg border border-gray-100 p-2 flex flex-col gap-2">
                                        <div className="h-1.5 w-12 bg-gray-200 rounded-full"></div>
                                        <div className="flex-1 flex items-end gap-1 px-1">
                                            <div className="w-2 flex-1 bg-gray-200 rounded-t-sm h-[40%]"></div>
                                            <div className="w-2 flex-1 bg-[#2A2B32] rounded-t-sm h-[80%]"></div>
                                            <div className="w-2 flex-1 bg-gray-200 rounded-t-sm h-[60%]"></div>
                                            <div className="w-2 flex-1 bg-[#2A2B32] rounded-t-sm h-[100%] hover:scale-105 transition-transform"></div>
                                            <div className="w-2 flex-1 bg-gray-200 rounded-t-sm h-[70%]"></div>
                                        </div>
                                    </div>

                                    <div className="flex flex-col gap-2">
                                        <div className="h-1.5 w-16 bg-gray-200 rounded-full mb-1"></div>
                                        <div className="flex items-center justify-between">
                                            <div className="h-2 w-14 bg-gray-100 rounded-full"></div>
                                            <div className="h-8 w-8 rounded-full border-[3px] border-green-500 border-r-gray-100"></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </motion.div>

        </section>
    );
};

export default Hero;

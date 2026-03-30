import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Lock, Zap, RefreshCw, ShieldAlert, FileSearch, Server, Target } from 'lucide-react';

/* --- Refined Micro-Animations --- */

const ScrambleTextAnim = () => {
    const [text, setText] = useState("SECURE_AUTH");
    useEffect(() => {
        const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*";
        const interval = setInterval(() => {
            setText(Array.from({ length: 11 }).map(() => chars[Math.floor(Math.random() * chars.length)]).join(''));
        }, 70);
        return () => clearInterval(interval);
    }, []);
    return (
        <div className="relative font-mono text-3xl md:text-4xl font-black tracking-[0.2em] text-gray-800 mix-blend-multiply flex items-center justify-center w-full h-full">
            {/* Subtle green glow behind the scrambling text */}
            <span className="absolute text-emerald-500 blur-[4px] opacity-40 z-0">{text}</span>
            <span className="relative z-10">{text}</span>
        </div>
    );
};

const RadarPulseAnim = () => (
    <div className="relative flex items-center justify-center w-full h-full">
        <motion.div animate={{ scale: [1, 3], opacity: [0.6, 0] }} transition={{ duration: 2.5, repeat: Infinity, ease: "easeOut" }} className="absolute w-12 h-12 border-[1.5px] border-cyan-400 rounded-full"></motion.div>
        <motion.div animate={{ scale: [1, 3], opacity: [0.6, 0] }} transition={{ duration: 2.5, delay: 1.25, repeat: Infinity, ease: "easeOut" }} className="absolute w-12 h-12 border-[1.5px] border-cyan-400 rounded-full"></motion.div>
        <div className="w-4 h-4 bg-cyan-500 rounded-full z-10 shadow-[0_0_15px_rgba(6,182,212,0.8)] border-2 border-white"></div>
    </div>
);

const MorphAnim = () => (
    <div className="relative flex items-center justify-center gap-6 w-full h-full">
        <motion.div animate={{ rotate: 180 }} transition={{ duration: 4, repeat: Infinity, ease: "linear" }} className="w-12 h-12 border-4 border-indigo-500 rounded-xl rounded-tr-[50%] opacity-80 shadow-[0_0_15px_rgba(99,102,241,0.4)]"></motion.div>
        <motion.div animate={{ x: [-15, 15, -15], scale: [1, 1.3, 1] }} transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }} className="absolute right-[20px] w-5 h-5 bg-fuchsia-500 rounded-full mix-blend-multiply blur-[1px] shadow-[0_0_10px_rgba(217,70,239,0.6)]"></motion.div>
        <motion.div animate={{ x: [15, -15, 15], scale: [1.3, 1, 1.3] }} transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }} className="absolute left-[20px] w-5 h-5 bg-blue-500 rounded-full mix-blend-multiply blur-[1px] shadow-[0_0_10px_rgba(59,130,246,0.6)]"></motion.div>
    </div>
);

const JITAnim = () => (
    <div className="relative w-16 h-16 flex items-center justify-center">
        <div className="absolute inset-0 border-2 border-dashed border-gray-300 rounded-2xl"></div>
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 4, repeat: Infinity, ease: "linear" }} className="absolute inset-[-6px]">
            <div className="w-3 h-3 bg-amber-400 rounded-full shadow-[0_0_12px_rgba(251,191,36,1)] blur-[0.5px]"></div>
        </motion.div>
        <Zap className="w-6 h-6 text-amber-500 opacity-90 drop-shadow-md z-10 relative" fill="currentColor" />
    </div>
);

const CodeAnim = () => (
    <div className="flex flex-col justify-center gap-[10px] w-full px-10">
        <div className="flex items-center gap-3">
            <span className="text-[11px] font-mono text-pink-500 font-bold tracking-wider">const</span>
            <div className="h-1.5 w-16 bg-gray-200 rounded-full overflow-hidden relative">
                <motion.div animate={{ x: ["-100%", "200%"] }} transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }} className="absolute inset-0 w-1/2 bg-blue-400 blur-[1px]"></motion.div>
            </div>
            <span className="text-[11px] font-mono text-gray-400 font-bold">=</span>
            <div className="h-1.5 w-12 bg-gray-300 rounded-full"></div>
        </div>
        <div className="flex items-center gap-3 pl-4 relative">
            <span className="text-[11px] font-mono text-purple-500 font-bold tracking-wider relative z-10">await</span>
            <div className="h-1.5 w-24 bg-gray-200 rounded-full overflow-hidden relative z-10">
                <motion.div animate={{ x: ["-100%", "300%"] }} transition={{ duration: 2, repeat: Infinity, delay: 0.5, ease: "linear" }} className="absolute inset-0 w-1/3 bg-emerald-400 blur-[1px]"></motion.div>
            </div>
            <motion.div animate={{ opacity: [0, 0.5, 0] }} transition={{ duration: 2, repeat: Infinity, delay: 0.5 }} className="absolute inset-0 bg-emerald-500/10 rounded-full blur-md z-0"></motion.div>
        </div>
        <div className="flex items-center gap-3">
            <span className="text-[11px] font-mono text-pink-500 font-bold tracking-wider">return</span>
            <div className="h-1.5 w-10 bg-gray-300 rounded-full"></div>
        </div>
    </div>
);

// New System Monitoring Animation: Server Node Map
const ServerNodeAnim = () => (
    <div className="relative w-full h-full flex items-center justify-center">
        {/* Central Server Node */}
        <div className="absolute z-20 w-14 h-14 bg-white rounded-xl shadow-lg border-2 border-indigo-500 flex items-center justify-center">
            <Server className="w-6 h-6 text-indigo-600" />
            <motion.div animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }} transition={{ duration: 2, repeat: Infinity }} className="absolute -bottom-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full border-2 border-white"></motion.div>
        </div>

        {/* Connecting Lines & Pings */}
        {[
            { angle: 0, length: 60, delay: 0 },
            { angle: 120, length: 70, delay: 0.5 },
            { angle: 240, length: 65, delay: 1 }
        ].map((line, i) => (
            <motion.div
                key={i}
                className="absolute w-[2px] bg-gray-200 origin-bottom"
                style={{ height: line.length, transform: `rotate(${line.angle}deg) translateY(-20px)` }}
            >
                <motion.div
                    animate={{ y: [0, -line.length] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: line.delay, ease: "linear" }}
                    className="w-[6px] h-[6px] rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)] absolute -left-[2px] bottom-0"
                ></motion.div>

                {/* Peripheral Nodes */}
                <div className="absolute -top-3 -left-2 w-5 h-5 bg-white border-2 border-gray-300 rounded-full"></div>
            </motion.div>
        ))}
    </div>
);

const SecurityAnim = () => (
    <div className="relative w-full h-full flex items-center justify-center">
        {/* Pulsing Aura */}
        <motion.div animate={{ scale: [1, 1.5, 1], opacity: [0.3, 0.1, 0.3] }} transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }} className="absolute w-20 h-20 bg-emerald-500 rounded-full blur-xl"></motion.div>

        {/* Rotating Hexagon Shield */}
        <motion.svg animate={{ rotate: 360 }} transition={{ duration: 15, repeat: Infinity, ease: "linear" }} className="absolute w-[110px] h-[110px] text-emerald-500/40 overflow-visible" viewBox="0 0 100 100">
            <polygon points="50 5, 89 25, 89 75, 50 95, 11 75, 11 25" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="4 6" />
            <polygon points="50 15, 80 32, 80 68, 50 85, 20 68, 20 32" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </motion.svg>

        {/* Central Core */}
        <div className="w-14 h-14 bg-white rounded-xl shadow-[0_4px_20px_rgba(16,185,129,0.2)] border border-emerald-100 flex items-center justify-center z-10 relative overflow-hidden">
            {/* Scanning Line overlay inside the core */}
            <motion.div animate={{ y: ["-100%", "100%"] }} transition={{ duration: 2.5, repeat: Infinity, ease: "linear" }} className="absolute inset-0 w-full h-1/2 bg-gradient-to-b from-transparent via-emerald-400/20 to-transparent"></motion.div>
            <ShieldAlert className="w-6 h-6 text-emerald-600 relative z-10" />
        </div>

        {/* Floating blocked anomalies outside the shield */}
        <motion.div animate={{ x: [25, 10, 25], y: [-25, -10, -25], opacity: [0, 1, 0] }} transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }} className="absolute right-4 top-8 w-2 h-2 bg-red-500 rounded-full border border-white shadow-sm"></motion.div>

        <motion.div animate={{ x: [-25, -10, -25], y: [25, 10, 25], opacity: [0, 1, 0] }} transition={{ duration: 3, repeat: Infinity, ease: "easeInOut", delay: 1 }} className="absolute left-4 bottom-8 w-2.5 h-2.5 bg-orange-500 rounded-sm border border-white shadow-sm"></motion.div>
    </div>
);

const ReportAnim = () => (
    <div className="relative w-16 h-[86px] border-[1.5px] border-gray-300 rounded-lg bg-white overflow-hidden shadow-lg flex flex-col items-center pt-3 gap-2.5">
        <div className="w-10 h-1 bg-gray-200 rounded-full"></div>
        <div className="w-8 h-1 bg-gray-200 rounded-full self-start ml-3"></div>
        <div className="w-10 h-1 bg-gray-200 rounded-full self-start ml-3"></div>
        <div className="w-6 h-1 bg-gray-200 rounded-full self-start ml-3"></div>
        <motion.div animate={{ y: [-5, 75, -5] }} transition={{ duration: 3, repeat: Infinity, ease: "linear" }} className="absolute top-0 left-0 right-0 h-[2.5px] bg-blue-500 shadow-[0_0_15px_rgba(59,130,246,1)] z-10"></motion.div>
    </div>
);

const ExplainAnim = () => (
    <div className="relative w-full h-full flex items-center justify-center">
        <svg className="absolute inset-0 w-full h-full overflow-visible pointer-events-none">
            {/* Draw animated gradient paths between nodes */}
            <motion.path d="M 40 70 Q 80 30 140 50" fill="none" stroke="url(#grad1)" strokeWidth="3" strokeLinecap="round" strokeDasharray="160" animate={{ strokeDashoffset: [160, 0] }} transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }} />
            <motion.path d="M 40 70 Q 100 110 160 80" fill="none" stroke="url(#grad2)" strokeWidth="3" strokeLinecap="round" strokeDasharray="160" animate={{ strokeDashoffset: [160, 0] }} transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }} />
            <defs>
                <linearGradient id="grad1"><stop offset="0%" stopColor="#8b5cf6" /><stop offset="100%" stopColor="#ec4899" /></linearGradient>
                <linearGradient id="grad2"><stop offset="0%" stopColor="#3b82f6" /><stop offset="100%" stopColor="#10b981" /></linearGradient>
            </defs>
        </svg>
        <div className="absolute left-[30px] top-[60px] w-5 h-5 bg-white border-[3px] border-gray-800 rounded-full shadow-[0_4px_10px_rgba(0,0,0,0.15)] z-10"></div>
        <div className="absolute left-[132px] top-[42px] w-4 h-4 bg-pink-500 rounded-full shadow-[0_0_12px_rgba(236,72,153,0.9)] z-10 border-2 border-white"></div>
        <div className="absolute left-[152px] top-[72px] w-4 h-4 bg-emerald-500 rounded-full shadow-[0_0_12px_rgba(16,185,129,0.9)] z-10 border-2 border-white"></div>
    </div>
);

// New Adaptive Skill Assessment Animation: Dynamic Line Chart
const AdaptiveChartAnim = () => (
    <div className="relative w-full h-[120px] flex items-end justify-between px-6 pb-4">
        {/* Subtle grid lines background */}
        <div className="absolute inset-x-6 top-4 bottom-4 flex flex-col justify-between opacity-10 pointer-events-none">
            <div className="w-full h-[1px] bg-gray-500"></div>
            <div className="w-full h-[1px] bg-gray-500"></div>
            <div className="w-full h-[1px] bg-gray-500"></div>
            <div className="w-full h-[1px] bg-gray-500"></div>
        </div>

        {/* Animated line path representing difficulty adjusting over time */}
        <svg className="absolute inset-0 w-full h-full overflow-visible" preserveAspectRatio="none">
            <motion.path
                d="M 24 90 C 50 90, 80 50, 120 70 C 160 90, 180 30, 220 50 C 260 70, 280 20, 320 40"
                fill="none"
                stroke="url(#gradientLine)"
                strokeWidth="4"
                strokeLinecap="round"
                className="drop-shadow-md"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: [0, 1, 1] }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            />
            <defs>
                <linearGradient id="gradientLine" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#8b5cf6" />
                    <stop offset="50%" stopColor="#ec4899" />
                    <stop offset="100%" stopColor="#f43f5e" />
                </linearGradient>
            </defs>
        </svg>

        {/* Data points along the curve */}
        <motion.div animate={{ scale: [0, 1, 0] }} transition={{ duration: 3, repeat: Infinity, times: [0, 0.2, 0.4] }} className="absolute left-[116px] top-[66px] w-3 h-3 bg-pink-500 rounded-full border-2 border-white shadow-sm z-10"></motion.div>

        <motion.div animate={{ scale: [0, 1, 0] }} transition={{ duration: 3, repeat: Infinity, times: [0, 0.5, 0.7] }} className="absolute left-[216px] top-[46px] w-3 h-3 bg-rose-500 rounded-full border-2 border-white shadow-sm z-10"></motion.div>

        <motion.div animate={{ scale: [0, 1, 0] }} transition={{ duration: 3, repeat: Infinity, times: [0, 0.8, 1] }} className="absolute left-[316px] top-[36px] w-3 h-3 bg-red-400 rounded-full border-2 border-white shadow-sm z-10"></motion.div>
    </div>
);

/* --- Feature Data --- */

const features = [
    { title: "Anti-OCR Display", desc: "Proprietary text rendering prevents illicit photos by rapidly alternating characters. It remains perfectly readable to the human eye, but registers as a scrambled blur to any camera lens.", anim: ScrambleTextAnim, cols: "md:col-span-2 lg:col-span-2 lg:row-span-2" },
    { title: "Real-time Intervention", desc: "Immediate automated actions to confidentially pause or intervene during an anomaly.", anim: RadarPulseAnim, cols: "md:col-span-1 lg:col-span-1" },
    { title: "LLM Morphing", desc: "Dynamically rewrites question phrasing on the fly, rendering cheat sheets useless.", anim: MorphAnim, cols: "md:col-span-1 lg:col-span-1" },
    { title: "J.I.T. Generation", desc: "Questions procedurally generated ms before rendering, preventing local caching.", anim: JITAnim, cols: "md:col-span-1 lg:col-span-1" },
    { title: "Code Analysis", desc: "Plagiarism checking in an isolated IDE analyzing raw candidate logic and ASTs.", anim: CodeAnim, cols: "md:col-span-1 lg:col-span-1" },
    { title: "System Monitoring", desc: "Comprehensive oversight of OS processes, USB devices, and virtual machines.", anim: ServerNodeAnim, cols: "md:col-span-2 lg:col-span-2" },
    { title: "Active Security", desc: "Continuous analysis of testing flow, hardware spoofing, and abnormal interactions.", anim: SecurityAnim, cols: "md:col-span-2 lg:col-span-2" },
    { title: "Evidentiary Reports", desc: "Detailed anomaly reports combining flags with synced video evidence.", anim: ReportAnim, cols: "md:col-span-1 lg:col-span-1" },
    { title: "Explainability", desc: "Clear, human-readable logic for why specific behaviors were flagged.", anim: ExplainAnim, cols: "md:col-span-1 lg:col-span-1" },
    { title: "Adaptive Skill Assessment", desc: "Intelligent selection adapting difficulty in real-time based on live performance markers, precisely measuring skill.", anim: AdaptiveChartAnim, cols: "md:col-span-2 lg:col-span-4" }
];

const Features = () => {
    return (
        <section id="features" className="py-24 px-6 md:px-12 max-w-[1400px] mx-auto">

            <motion.div
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.7 }}
                className="text-center mb-24 max-w-3xl mx-auto flex flex-col items-center"
            >
                {/* Minimalist Geometric Dot & Line */}
                <div className="flex flex-col items-center justify-center gap-3 mb-8">
                    <div className="w-1.5 h-1.5 bg-gray-900 rounded-full"></div>
                    <div className="w-[1px] h-12 bg-gradient-to-b from-gray-900 to-transparent"></div>
                </div>

                <h3 className="text-4xl md:text-5xl font-medium tracking-tight text-gray-900 leading-[1.2] mb-6">
                    Engineering absolute trust <br className="hidden md:block" /> into every assessment.
                </h3>

                <p className="text-[17px] text-gray-500 font-normal leading-relaxed max-w-xl mx-auto">
                    A comprehensive suite of automated countermeasures operating silently at the system level.
                </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 auto-rows-[minmax(0,1fr)]">
                {features.map((feature, index) => {
                    const AnimationComponent = feature.anim;
                    // For the Anti-OCR card (which is index 0), increase the height of the animation container
                    const isAntiOCR = index === 0;

                    return (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, margin: "-50px" }}
                            transition={{ duration: 0.5, delay: index * 0.05 }}
                            className={`group relative flex flex-col justify-between p-8 rounded-[32px] border border-gray-200 bg-white shadow-sm hover:shadow-xl transition-all duration-500 overflow-hidden hover:border-gray-300 ${feature.cols}`}
                        >
                            <div className={`bg-[#FAFAFA] rounded-2xl flex items-center justify-center relative overflow-hidden transition-colors duration-500 border border-gray-100 shadow-inner group-hover:bg-gray-50/50 ${isAntiOCR ? 'h-64 mb-8' : 'h-44 mb-8'}`}>
                                <AnimationComponent />
                            </div>

                            <div className="relative z-10 mt-auto">
                                <h4 className="text-2xl font-bold tracking-tight text-gray-900 mb-2">
                                    {feature.title}
                                </h4>
                                <p className="text-gray-500 leading-relaxed text-[15px] font-medium">
                                    {feature.desc}
                                </p>
                            </div>
                        </motion.div>
                    );
                })}
            </div>

        </section>
    );
};

export default Features;

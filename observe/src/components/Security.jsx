import React from 'react';
import { motion } from 'framer-motion';

const Security = () => {
    return (
        <section id="security" className="relative bg-[#FAFAFA] text-gray-900 py-32 md:py-48 px-6 overflow-hidden flex items-center justify-center min-h-[80vh]">

            {/* Elegant soft mesh gradient background using Framer Motion */}
            <div className="absolute inset-0 pointer-events-none opacity-50 z-0">
                <motion.div
                    animate={{
                        x: [0, 50, 0, -50, 0],
                        y: [0, 30, -30, 0, 0],
                        scale: [1, 1.1, 1]
                    }}
                    transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                    className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] bg-indigo-100 rounded-full mix-blend-multiply blur-[100px]"
                ></motion.div>

                <motion.div
                    animate={{
                        x: [0, -40, 0, 40, 0],
                        y: [0, -40, 30, 0, 0],
                        scale: [1, 1.2, 1]
                    }}
                    transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
                    className="absolute top-[20%] right-[-10%] w-[40vw] h-[40vw] bg-rose-100 rounded-full mix-blend-multiply blur-[100px]"
                ></motion.div>

                <motion.div
                    animate={{
                        x: [0, 30, -40, 0, 0],
                        y: [0, 50, -20, 0, 0],
                        scale: [1, 1.1, 1]
                    }}
                    transition={{ duration: 22, repeat: Infinity, ease: "linear" }}
                    className="absolute bottom-[-20%] left-[20%] w-[60vw] h-[60vw] bg-teal-100 rounded-full mix-blend-multiply blur-[100px]"
                ></motion.div>
            </div>

            <div className="relative z-10 text-center max-w-4xl mx-auto flex flex-col items-center">

                {/* Micro-label */}
                <motion.div
                    initial={{ opacity: 0, y: 15 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-gray-200 text-gray-600 text-xs font-bold tracking-widest uppercase mb-12 shadow-sm"
                >
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    Verified Privacy
                </motion.div>

                {/* Massive, elegant headline with subtle text gradient */}
                <motion.h2
                    className="text-[60px] md:text-[90px] lg:text-[110px] font-semibold tracking-tighter text-transparent bg-clip-text bg-gradient-to-br from-gray-900 via-gray-700 to-gray-500 mb-8 leading-[1.05]"
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                >
                    Zero <br className="hidden md:block" /> Knowledge.
                </motion.h2>

                {/* Minimalist supporting text */}
                <motion.p
                    className="text-xl md:text-2xl text-gray-500 font-medium leading-relaxed max-w-2xl mx-auto mb-14"
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.8, delay: 0.2 }}
                >
                    Mathematical certainty over your data. We cannot see, read, or harvest your information. The keys belong to you alone.
                </motion.p>

                {/* Clean, high-contrast button */}
                <motion.button
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.8, delay: 0.4 }}
                    className="group flex items-center justify-center gap-3 px-8 py-4 bg-gray-900 text-white rounded-full text-[15px] font-semibold hover:bg-gray-800 hover:scale-105 hover:shadow-xl hover:shadow-gray-900/20 transition-all duration-300"
                >
                    Read Security Protocol
                    <span className="group-hover:translate-x-1 transition-transform duration-300">→</span>
                </motion.button>

            </div>
        </section>
    );
};

export default Security;

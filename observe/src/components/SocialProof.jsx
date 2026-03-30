import React from 'react';
import { motion } from 'framer-motion';

// Complex abstract SVGs representing different types of institutions
const logos = [
    // Abstract "Tech" Corp (Geometric)
    <svg key="1" width="120" height="40" viewBox="0 0 120 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="opacity-40 hover:opacity-100 transition-opacity duration-300 grayscale"><path d="M20 10H30V30H20V10Z" fill="currentColor" /><path d="M35 15H45V30H35V15Z" fill="currentColor" /><path d="M50 20H60V30H50V20Z" fill="currentColor" /><circle cx="75" cy="20" r="10" stroke="currentColor" strokeWidth="3" /><path d="M90 10L100 30H110L100 10H90Z" fill="currentColor" /></svg>,
    // Abstract "University" (Shield/Crest)
    <svg key="2" width="120" height="40" viewBox="0 0 120 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="opacity-40 hover:opacity-100 transition-opacity duration-300 grayscale"><path d="M20 5C20 5 30 15 30 25C30 35 20 35 20 35C20 35 10 35 10 25C10 15 20 5 20 5Z" stroke="currentColor" strokeWidth="2" /><path d="M20 10V30" stroke="currentColor" strokeWidth="2" /><path d="M14 20H26" stroke="currentColor" strokeWidth="2" /><text x="40" y="26" fill="currentColor" fontFamily="serif" fontSize="20" fontWeight="bold" letterSpacing="2">STANFORD</text></svg>,
    // Abstract "Global Enterprise"
    <svg key="3" width="140" height="40" viewBox="0 0 140 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="opacity-40 hover:opacity-100 transition-opacity duration-300 grayscale"><circle cx="20" cy="20" r="14" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" /><circle cx="20" cy="20" r="8" fill="currentColor" /><text x="45" y="26" fill="currentColor" fontFamily="sans-serif" fontSize="20" fontWeight="900" letterSpacing="-1">GLOBALTECH</text></svg>,
    // Abstract "Research Institute" (MIT style)
    <svg key="4" width="100" height="40" viewBox="0 0 100 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="opacity-40 hover:opacity-100 transition-opacity duration-300 grayscale"><rect x="10" y="10" width="8" height="20" fill="currentColor" /><rect x="22" y="10" width="8" height="20" fill="currentColor" /><rect x="34" y="10" width="8" height="20" fill="currentColor" /><rect x="46" y="10" width="30" height="8" fill="currentColor" /><rect x="57" y="22" width="8" height="8" fill="currentColor" /></svg>,
    // Abstract "Modern Startup"
    <svg key="5" width="130" height="40" viewBox="0 0 130 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="opacity-40 hover:opacity-100 transition-opacity duration-300 grayscale"><path d="M10 20L20 10H30L20 20L30 30H20L10 20Z" fill="currentColor" /><path d="M25 20L35 10H45L35 20L45 30H35L25 20Z" fill="currentColor" /><text x="55" y="26" fill="currentColor" fontFamily="sans-serif" fontSize="18" fontWeight="600" letterSpacing="1">NEXUS</text></svg>,
    // Abstract "Classic University" (Oxford Style)
    <svg key="6" width="130" height="40" viewBox="0 0 130 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="opacity-40 hover:opacity-100 transition-opacity duration-300 grayscale"><rect x="10" y="5" width="20" height="30" rx="2" stroke="currentColor" strokeWidth="2" /><path d="M10 15H30" stroke="currentColor" strokeWidth="2" /><path d="M20 15V35" stroke="currentColor" strokeWidth="2" /><text x="40" y="26" fill="currentColor" fontFamily="serif" fontSize="22" fontWeight="normal" fontStyle="italic">Oxford</text></svg>,
];

const SocialProof = () => {
    return (
        <section className="py-20 border-b border-gray-100 bg-white overflow-hidden relative">

            <div className="absolute inset-0 max-w-[1400px] mx-auto opacity-100 pointer-events-none z-10 flex justify-between">
                <div className="w-40 h-full bg-gradient-to-r from-white to-transparent"></div>
                <div className="w-40 h-full bg-gradient-to-l from-white to-transparent"></div>
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.6 }}
                className="text-center mb-12 text-[12px] font-bold uppercase tracking-[0.25em] text-gray-400"
            >
                Securing assessments for leading enterprises & universities
            </motion.div>

            <div className="relative w-full flex overflow-hidden">
                <motion.div
                    className="flex whitespace-nowrap gap-20 items-center min-w-max px-10"
                    animate={{ x: [0, -1500] }}
                    transition={{
                        repeat: Infinity,
                        ease: "linear",
                        duration: 35
                    }}
                >
                    {/* Triple array for guaranteed seamless looping on ultra-wide screens */}
                    {[...logos, ...logos, ...logos].map((Logo, i) => (
                        <div key={i} className="flex-shrink-0 text-black">
                            {Logo}
                        </div>
                    ))}
                </motion.div>
            </div>
        </section>
    );
};

export default SocialProof;

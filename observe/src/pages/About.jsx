import React from 'react';
import { motion } from 'framer-motion';

const About = () => {
    return (
        <div className="min-h-screen bg-white pb-20 pt-32">
            <div className="max-w-[1000px] mx-auto px-6 text-center mb-20">
                <motion.h1 
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                    className="text-5xl md:text-7xl font-bold tracking-tight text-gray-900 mb-6"
                >
                    Redefining Trust in <br className="hidden md:block" />Digital Assessments
                </motion.h1>
                <motion.p 
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
                    className="text-xl text-gray-500 max-w-3xl mx-auto leading-relaxed"
                >
                    At Observe, our mission is to provide an uncompromised, sophisticated, and incredibly beautiful platform for evaluating talent globally. We believe technology should empower honesty seamlessly.
                </motion.p>
            </div>

            <div className="max-w-[1200px] mx-auto px-6 mb-32">
                <div className="relative rounded-[3rem] overflow-hidden shadow-2xl">
                    <img src="https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&q=80&w=2000" alt="Team collaborating" className="w-full h-[300px] md:h-[500px] object-cover" />
                    <div className="absolute inset-0 bg-indigo-900/20 mix-blend-multiply transition-colors hover:bg-transparent duration-700"></div>
                </div>
            </div>

            <div className="bg-[#F8FAFC] py-32 border-y border-gray-100">
                <div className="max-w-[1200px] mx-auto px-6 text-center">
                    <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-16">The Leadership Team</h2>
                    <div className="grid md:grid-cols-3 gap-10">
                        {[
                            { name: "Sarah Jenkins", role: "Chief Executive Officer", img: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&q=80&w=400" },
                            { name: "David Chen", role: "Chief Technology Officer", img: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=400" },
                            { name: "Elena Rodriguez", role: "Head of Product", img: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&q=80&w=400" },
                        ].map((member, i) => (
                            <motion.div 
                                key={member.name}
                                initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}
                            >
                                <div className="w-48 h-48 mx-auto rounded-full overflow-hidden mb-6 border-4 border-white shadow-xl group cursor-pointer">
                                    <img src={member.img} alt={member.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" />
                                </div>
                                <h3 className="text-xl font-bold text-gray-900">{member.name}</h3>
                                <p className="text-indigo-600 font-medium">{member.role}</p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default About;

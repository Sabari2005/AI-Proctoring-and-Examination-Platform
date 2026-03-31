import React from 'react';
import { motion } from 'framer-motion';

const SabariPhoto = '/Sabari.jpeg';
const UvarajanPhoto = '/Uvarajan.jpeg';
const SarathiPhoto = '/Sarathi.jpeg';
const KaviarasuPhoto = '/kaviarasu.jpeg';
const swathiPhoto = '/swathi.jpeg';

const leadershipMembers = [
    { name: "Sabari Vadivelan S", role: "AI & Backend Developer", img: SabariPhoto },
    { name: "Uvarajan D", role: "API & Backend Developer", img: UvarajanPhoto },
    { name: "Kaviarasu K", role: "UI/UX Developer & Motion Graphics", img: KaviarasuPhoto },
    { name: "Sarathi S", role: "Web Developer", img: SarathiPhoto },
    { name: "Swathi S", role: "Web Developer", img: swathiPhoto },
];

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

            <div className="relative overflow-hidden bg-[radial-gradient(circle_at_top,#f3f8ff_0%,#f8fafc_52%,#ffffff_100%)] py-32 border-y border-slate-200">
                <div className="pointer-events-none absolute -top-24 -left-24 h-72 w-72 rounded-full bg-cyan-200/35 blur-3xl"></div>
                <div className="pointer-events-none absolute -bottom-20 -right-20 h-72 w-72 rounded-full bg-indigo-200/35 blur-3xl"></div>
                <div className="max-w-[1200px] mx-auto px-6 text-center">
                    <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-16">The Leadership Team</h2>
                    {/*
                      Legacy profile display (kept as requested):
                      <div className="max-w-[1000px] mx-auto flex flex-wrap justify-center gap-x-20 gap-y-6">
                          {[
                              { name: "Sabari Vadivelan S", role: "AI & Backend Developer", img: SabariPhoto },
                              { name: "Uvarajan D", role: "API & Backend Developer", img: UvarajanPhoto },
                              { name: "Kaviarasu K", role: "UI/UX & Graphics Designer", img: KaviarasuPhoto },
                              { name: "Sarathi S", role: "Web Developer", img: SarathiPhoto },
                              { name: "Swathi S", role: "Web Developer", img: swathiPhoto },
                          ].map((member, i) => (
                              <motion.div
                                  key={member.name}
                                  className="w-[240px]"
                                  initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}
                              >
                                  <div className="w-48 h-48 mx-auto rounded-2xl overflow-hidden mb-6 border-4 border-white shadow-xl group cursor-pointer">
                                      <img src={member.img} alt={member.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" />
                                  </div>
                                  <h3 className="text-[1.85rem] md:text-[2.15rem] font-serif font-medium italic tracking-[0.035em] text-zinc-900 leading-none">{member.name}</h3>
                                  <p className="text-indigo-600 font-medium">{member.role}</p>
                              </motion.div>
                          ))}
                      </div>
                    */}

                    <div className="relative z-10 max-w-[1020px] mx-auto flex flex-wrap justify-center gap-8">
                        {leadershipMembers.map((member, i) => (
                            <motion.article
                                key={member.name}
                                className="group relative h-[430px] w-full overflow-hidden rounded-3xl border border-slate-200/80 text-left shadow-[0_14px_36px_rgba(15,23,42,0.14)] transition-all duration-500 hover:-translate-y-1.5 hover:shadow-[0_22px_44px_rgba(14,116,144,0.22)] sm:w-[300px]"
                                initial={{ opacity: 0, y: 18 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: i * 0.08 }}
                            >
                                <img
                                    src={member.img}
                                    alt={member.name}
                                    className="absolute inset-0 h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
                                />

                                <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-slate-900/70 via-slate-900/10 to-transparent"></div>
                                <div className="pointer-events-none absolute inset-0 ring-1 ring-white/35"></div>

                                <motion.div
                                    className="absolute inset-x-4 bottom-4 rounded-2xl border border-white/40 bg-white/22 p-4 backdrop-blur-md transition-all duration-500 group-hover:border-white/60 group-hover:bg-white/28"
                                    initial={{ opacity: 0, y: 12 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    viewport={{ once: true }}
                                    transition={{ delay: 0.2 + i * 0.08, duration: 0.45 }}
                                >
                                    <h3 className="text-[1.2rem] font-semibold tracking-tight text-white drop-shadow-[0_1px_8px_rgba(15,23,42,0.35)]">{member.name}</h3>
                                    <p className="mt-1 text-xs font-semibold uppercase tracking-[0.1em] text-white/90">{member.role}</p>
                                </motion.div>
                            </motion.article>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default About;

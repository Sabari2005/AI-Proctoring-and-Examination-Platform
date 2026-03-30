import React from 'react';
import { motion } from 'framer-motion';

const Contact = () => {
    return (
        <div className="min-h-screen bg-white flex flex-col items-center justify-center text-center px-6 py-20">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4 }}
                className="w-full max-w-lg p-10 rounded-3xl border border-gray-100 shadow-xl bg-white"
            >
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gray-100 text-gray-600 text-xs font-bold tracking-widest uppercase mb-6">
                    Connect With Us
                </div>
                <h1 className="text-4xl font-bold tracking-tight text-gray-900 mb-4">Book a Demo</h1>
                <p className="text-gray-500 mb-8 leading-relaxed">
                    Schedule a personalized walkthrough of the Observe platform. Learn how we can secure your institutional exams.
                </p>

                <form className="flex flex-col gap-4 text-left" onSubmit={(e) => e.preventDefault()}>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1 ml-1">First Name</label>
                            <input type="text" placeholder="John" className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1 ml-1">Last Name</label>
                            <input type="text" placeholder="Doe" className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900" />
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 ml-1">Work Email</label>
                        <input type="email" placeholder="john@university.edu" className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 ml-1">Organization / Institution</label>
                        <input type="text" placeholder="University Name" className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 ml-1">How can we help?</label>
                        <textarea placeholder="Tell us about your requirements..." rows={4} className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900 resize-none"></textarea>
                    </div>
                    <button type="submit" className="w-full px-4 py-3 rounded-xl bg-gray-900 text-white font-semibold hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 mt-2">
                        Request Walkthrough
                    </button>
                </form>
            </motion.div>
        </div>
    );
};

export default Contact;

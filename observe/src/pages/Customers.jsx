import React from 'react';
import { motion } from 'framer-motion';

const Customers = () => {
    return (
        <div className="min-h-[80vh] pt-32 pb-20 bg-white flex flex-col items-center justify-center text-center px-6">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
            >
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gray-100 text-gray-600 text-xs font-bold tracking-widest uppercase mb-6">
                    Case Studies
                </div>
                <h1 className="text-5xl md:text-7xl font-semibold tracking-tight text-gray-900 mb-6">Customers</h1>
                <p className="text-xl text-gray-500 max-w-2xl mx-auto">See how top institutions trust Observe. This page is under construction.</p>
            </motion.div>
        </div>
    );
};

export default Customers;

import React from 'react';
import { motion } from 'framer-motion';
import { Check } from 'lucide-react';
import { Link } from 'react-router-dom';

const plans = [
    {
        name: "Starter",
        desc: "Essential features for small institutions getting started with online proctoring.",
        price: "$99",
        billing: "/month",
        features: [
            "Up to 500 exams per month",
            "Basic AI Anomaly Detection",
            "7-day video retention",
            "Standard email support",
            "LMS Integration (Canvas, Moodle)"
        ],
        cta: "Start Free Trial",
        link: "/register",
        popular: false
    },
    {
        name: "Professional",
        desc: "Advanced security and analytics for growing universities and certification bodies.",
        price: "$299",
        billing: "/month",
        features: [
            "Up to 2,000 exams per month",
            "Advanced Multi-model AI Analysis",
            "30-day video retention",
            "Priority 24/7 support",
            "Custom API Access",
            "Detailed Analytics Dashboard"
        ],
        cta: "Get Started",
        link: "/register",
        popular: true
    },
    {
        name: "Enterprise",
        desc: "Zero-knowledge architecture and custom deployments for massive scale operations.",
        price: "Custom",
        billing: "Pricing",
        features: [
            "Unlimited exams",
            "Dedicated Account Manager",
            "Custom Data Localization",
            "SOC 2 Type II & GDPR Verified",
            "Custom Retention Policies",
            "White-labeled platform"
        ],
        cta: "Contact Sales",
        link: "/contact",
        popular: false
    }
];

const Pricing = () => {
    return (
        <div className="min-h-screen pt-32 pb-32 bg-[#FAFAFA] text-gray-900 relative">
            <div className="max-w-[1200px] mx-auto px-6 relative z-10">

                {/* Header */}
                <div className="text-center max-w-3xl mx-auto mb-20 flex flex-col items-center">
                    <motion.div
                        initial={{ opacity: 0, y: 15 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true, margin: "-50px" }}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-gray-200 text-gray-600 text-xs font-bold tracking-widest uppercase mb-8 shadow-sm"
                    >
                        Transparent Plans
                    </motion.div>

                    <motion.h1
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true, margin: "-50px" }}
                        transition={{ delay: 0.1 }}
                        className="text-5xl md:text-7xl font-semibold tracking-tighter text-gray-900 mb-6"
                    >
                        Simple, scaleable pricing.
                    </motion.h1>

                    <motion.p
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true, margin: "-50px" }}
                        transition={{ delay: 0.2 }}
                        className="text-xl text-gray-500 max-w-2xl mx-auto"
                    >
                        Whether you are testing 100 students or 100,000, we have a scientifically-verifiable privacy package for you.
                    </motion.p>
                </div>

                {/* Pricing Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {plans.map((plan, index) => (
                        <motion.div
                            key={plan.name}
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, margin: "-50px" }}
                            transition={{ delay: 0.3 + index * 0.1 }}
                            className={`relative flex flex-col p-8 rounded-3xl border transition-all duration-300 ${plan.popular
                                ? 'bg-[#050505] text-white border-black shadow-2xl scale-[1.02]'
                                : 'bg-white text-gray-900 border-gray-200 shadow-sm hover:shadow-lg hover:border-gray-300'
                                }`}
                        >
                            {plan.popular && (
                                <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 px-4 py-1.5 bg-indigo-500 text-white text-xs font-bold tracking-wider rounded-full shadow-lg">
                                    MOST POPULAR
                                </div>
                            )}

                            <div className="mb-8">
                                <h3 className={`text-2xl font-bold mb-2 ${plan.popular ? 'text-white' : 'text-gray-900'}`}>{plan.name}</h3>
                                <p className={`text-sm leading-relaxed ${plan.popular ? 'text-gray-400' : 'text-gray-500'}`}>{plan.desc}</p>
                            </div>

                            <div className="mb-8 flex items-baseline gap-2">
                                <span className={`text-5xl font-bold tracking-tight ${plan.popular ? 'text-white' : 'text-gray-900'}`}>{plan.price}</span>
                                <span className={`text-sm font-medium ${plan.popular ? 'text-gray-400' : 'text-gray-500'}`}>{plan.billing}</span>
                            </div>

                            <Link
                                to={plan.link}
                                className={`w-full py-4 rounded-xl text-sm font-semibold text-center transition-all duration-300 mb-10 ${plan.popular
                                    ? 'bg-white text-black hover:bg-gray-100 hover:scale-[1.02]'
                                    : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                                    }`}
                            >
                                {plan.cta}
                            </Link>

                            <div className="flex-grow space-y-4">
                                <p className={`text-sm font-semibold uppercase tracking-wider mb-6 ${plan.popular ? 'text-gray-300' : 'text-gray-900'}`}>Includes:</p>
                                {plan.features.map(feature => (
                                    <div key={feature} className="flex items-start gap-3">
                                        <div className={`mt-0.5 p-1 rounded-full ${plan.popular ? 'bg-white/10 text-white' : 'bg-gray-100 text-gray-900'}`}>
                                            <Check className="w-3 h-3 stroke-[3]" />
                                        </div>
                                        <span className={`text-sm leading-relaxed ${plan.popular ? 'text-gray-300' : 'text-gray-600'}`}>
                                            {feature}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    ))}
                </div>

            </div>
        </div>
    );
};

export default Pricing;

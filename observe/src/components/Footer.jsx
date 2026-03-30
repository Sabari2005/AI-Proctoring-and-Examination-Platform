import React from 'react';
import { Link } from 'react-router-dom';
import { Twitter, Github, Linkedin, ArrowRight } from 'lucide-react';

const footerLinks = {
    Product: [
        { name: 'Features', to: '/#features' },
        { name: 'Security', to: '/#security' },
        { name: 'Integrations', to: '/' },
        { name: 'Pricing', to: '/pricing' },
        { name: 'Changelog', to: '/' },
    ],
    Resources: [
        { name: 'Documentation', to: '/docs' },
        { name: 'API Reference', to: '/docs' },
        { name: 'Help Center', to: '/docs' },
        { name: 'Community', to: '/community' },
        { name: 'Blog', to: '/blog' },
    ],
    Company: [
        { name: 'About', to: '/about' },
        { name: 'Careers', to: '/' },
        { name: 'Customers', to: '/customers' },
        { name: 'Contact Us', to: '/' },
        { name: 'Partners', to: '/' },
    ],
    Legal: [
        { name: 'Privacy Policy', to: '/' },
        { name: 'Terms of Service', to: '/' },
        { name: 'Cookie Policy', to: '/' },
        { name: 'Security Protocol', to: '/#security' },
    ]
};

const Footer = () => {
    return (
        <footer className="bg-[#050505] text-white pt-24 pb-12 px-6 border-t border-white/10">
            <div className="max-w-[1200px] mx-auto">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-12 lg:gap-8 mb-20">

                    {/* Brand & Newsletter Column */}
                    <div className="lg:col-span-2 flex flex-col items-start pr-0 lg:pr-12">
                        <div className="flex items-center gap-3 mb-8">
                            <img src="/logo.svg" alt="Observe Logo" className="h-16 brightness-0 invert opacity-90" />
                        </div>

                        <p className="text-gray-400 text-sm leading-relaxed mb-8 max-w-sm">
                            The zero-knowledge, mathematically secure proctoring engine for enterprise and academic institutions.
                        </p>

                        <div className="w-full">
                            <p className="text-sm font-semibold text-white mb-4">Subscribe to updates</p>
                            <form className="relative flex items-center" onSubmit={(e) => e.preventDefault()}>
                                <input
                                    type="email"
                                    placeholder="Enter your email"
                                    className="w-full bg-white/5 border border-white/10 rounded-full px-5 py-3 text-sm text-white placeholder:text-gray-500 focus:outline-none focus:border-white/30 focus:bg-white/10 transition-all pr-12"
                                />
                                <button type="submit" className="absolute right-2 p-2 bg-white text-black rounded-full hover:scale-105 active:scale-95 transition-transform">
                                    <ArrowRight className="w-4 h-4" />
                                </button>
                            </form>
                        </div>
                    </div>

                    {/* Links Columns */}
                    {Object.entries(footerLinks).map(([category, links]) => (
                        <div key={category} className="lg:col-span-1">
                            <h3 className="text-sm font-semibold text-white mb-6 uppercase tracking-wider">{category}</h3>
                            <ul className="flex flex-col space-y-4">
                                {links.map((link) => (
                                    <li key={link.name}>
                                        <Link
                                            to={link.to}
                                            className="text-sm text-gray-400 hover:text-white transition-colors"
                                        >
                                            {link.name}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>

                {/* Bottom Bar */}
                <div className="pt-8 border-t border-white/10 flex flex-col md:flex-row items-center justify-between gap-6">
                    <p className="text-gray-500 text-sm">
                        &copy; {new Date().getFullYear()} Observe Inc. All rights reserved.
                    </p>

                    {/* Socials */}
                    <div className="flex items-center gap-6">
                        <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-white transition-colors">
                            <span className="sr-only">Twitter</span>
                            <Twitter className="w-5 h-5" />
                        </a>
                        <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-white transition-colors">
                            <span className="sr-only">GitHub</span>
                            <Github className="w-5 h-5" />
                        </a>
                        <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-white transition-colors">
                            <span className="sr-only">LinkedIn</span>
                            <Linkedin className="w-5 h-5" />
                        </a>
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default Footer;

import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronDown, BookOpen, Rss, Info, Users } from 'lucide-react';

const Navbar = () => {
    const [isResourcesOpen, setIsResourcesOpen] = useState(false);
    const dropdownRef = useRef(null);
    const location = useLocation();

    // Close dropdown when picking an item or clicking outside
    useEffect(() => {
        setIsResourcesOpen(false);
    }, [location]);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsResourcesOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const isHome = location.pathname === '/';

    return (
        <nav className="fixed top-0 left-0 right-0 z-50 bg-white/70 backdrop-blur-md border-b border-gray-100 border-t-[4px] border-t-[#2A2B32]">
            <div className="max-w-[1400px] mx-auto px-6 h-16 flex items-center justify-between">

                {/* Left Side: Logo and Links */}
                <div className="flex items-center gap-10">
                    <Link to="/" className="flex items-center gap-2">
                        <img src="/logo.svg" alt="Observe Logo" className="h-16" />
                    </Link>

                    <div className="hidden md:flex items-center space-x-2">
                        <a href="/#features" className="flex items-center gap-1.5 px-3 py-1.5 text-[14px] font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors">
                            Features
                        </a>
                        <Link to="/pricing" className="flex items-center gap-1.5 px-3 py-1.5 text-[14px] font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors">
                            Pricing
                        </Link>
                        <Link to="/customers" className="flex items-center gap-1.5 px-3 py-1.5 text-[14px] font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors">
                            Customers
                        </Link>

                        {/* Resources Dropdown */}
                        <div className="relative" ref={dropdownRef}>
                            <button
                                onClick={() => setIsResourcesOpen(!isResourcesOpen)}
                                className={`flex items-center gap-1.5 px-3 py-1.5 text-[14px] font-medium rounded-md transition-colors ${isResourcesOpen ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
                            >
                                Resources <ChevronDown className={`w-3.5 h-3.5 stroke-[2.5] transition-transform ${isResourcesOpen ? 'rotate-180 text-gray-900' : 'text-gray-400'}`} />
                            </button>

                            {/* Dropdown Menu */}
                            {isResourcesOpen && (
                                <div className="absolute top-[calc(100%+8px)] left-0 w-64 bg-white rounded-xl shadow-xl border border-gray-100 p-2 transform origin-top animate-in fade-in slide-in-from-top-2 duration-200">
                                    <Link to="/docs" className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors group">
                                        <div className="p-2 rounded-lg bg-gray-50 text-gray-500 group-hover:bg-white group-hover:text-gray-900 shadow-sm border border-transparent group-hover:border-gray-200 transition-all">
                                            <BookOpen className="w-4 h-4" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-gray-900 mb-0.5">Documentation</p>
                                            <p className="text-xs text-gray-500">Guides and API references</p>
                                        </div>
                                    </Link>
                                    <Link to="/blog" className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors group">
                                        <div className="p-2 rounded-lg bg-gray-50 text-gray-500 group-hover:bg-white group-hover:text-gray-900 shadow-sm border border-transparent group-hover:border-gray-200 transition-all">
                                            <Rss className="w-4 h-4" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-gray-900 mb-0.5">Blog</p>
                                            <p className="text-xs text-gray-500">Updates and industry insights</p>
                                        </div>
                                    </Link>
                                    <Link to="/about" className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors group">
                                        <div className="p-2 rounded-lg bg-gray-50 text-gray-500 group-hover:bg-white group-hover:text-gray-900 shadow-sm border border-transparent group-hover:border-gray-200 transition-all">
                                            <Info className="w-4 h-4" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-gray-900 mb-0.5">About Us</p>
                                            <p className="text-xs text-gray-500">Our mission and team</p>
                                        </div>
                                    </Link>
                                    <Link to="/community" className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors group">
                                        <div className="p-2 rounded-lg bg-gray-50 text-gray-500 group-hover:bg-white group-hover:text-gray-900 shadow-sm border border-transparent group-hover:border-gray-200 transition-all">
                                            <Users className="w-4 h-4" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-gray-900 mb-0.5">Community</p>
                                            <p className="text-xs text-gray-500">Join the discussion</p>
                                        </div>
                                    </Link>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Right Side: Actions */}
                <div className="flex items-center gap-5">
                    <Link to="/login" className="hidden md:block text-[14px] font-medium text-gray-500 hover:text-gray-900 transition-colors px-1">
                        Login
                    </Link>
                    <div className="flex items-center gap-3">
                        <Link to="/contact" className="hidden md:block px-3.5 py-1.5 text-[14px] font-medium text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
                            Book a demo
                        </Link>
                        <Link to="/register" className="px-3.5 py-1.5 text-[14px] font-medium text-white bg-[#2A2B32] rounded-md hover:bg-[#1f2025] transition-colors shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
                            Start for free
                        </Link>
                    </div>
                </div>

            </div>
        </nav>
    );
};

export default Navbar;

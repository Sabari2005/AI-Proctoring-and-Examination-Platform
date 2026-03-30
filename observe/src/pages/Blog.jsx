import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Calendar, Clock } from 'lucide-react';

const Blog = () => {
    const featuredPost = {
        title: "The Future of AI in Remote Proctoring",
        excerpt: "Discover how advanced machine learning models are revolutionizing the way we ensure exam integrity, reducing false positives while catching sophisticated cheating methods.",
        category: "Technology",
        date: "Oct 12, 2025",
        readTime: "8 min read",
        image: "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&q=80&w=2000"
    };

    const posts = [
        {
            id: 1,
            title: "Scaling Assessments to 100k Concurrent Users",
            category: "Engineering",
            date: "Sep 28, 2025",
            readTime: "12 min read",
            image: "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&q=80&w=800"
        },
        {
            id: 2,
            title: "Balancing Security and Candidate Privacy",
            category: "Compliance",
            date: "Sep 15, 2025",
            readTime: "6 min read",
            image: "https://images.unsplash.com/photo-1563986768494-4dee2763ff0f?auto=format&fit=crop&q=80&w=800"
        },
        {
            id: 3,
            title: "New Feature: Just-In-Time Exam Generation",
            category: "Product",
            date: "Sep 02, 2025",
            readTime: "4 min read",
            image: "https://images.unsplash.com/photo-1633356122544-f134324a6cee?auto=format&fit=crop&q=80&w=800"
        }
    ];

    return (
        <div className="min-h-screen bg-[#F8FAFC] pb-20 pt-28">
            <div className="max-w-[1200px] mx-auto px-6">
                
                <div className="text-center max-w-3xl mx-auto mb-16">
                    <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-gray-900 mb-6">Latest from Observe</h1>
                    <p className="text-xl text-gray-500">Product updates, engineering deep dives, and thoughts on the future of assessment integrity.</p>
                </div>

                {/* Featured Post */}
                <motion.div 
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
                    className="relative rounded-[2rem] overflow-hidden bg-gray-900 group cursor-pointer mb-16 shadow-lg border border-gray-800"
                >
                    <div className="absolute inset-0 w-full h-full">
                        <img src={featuredPost.image} alt={featuredPost.title} className="w-full h-full object-cover opacity-40 group-hover:scale-105 transition-transform duration-700" />
                        <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-gray-900/60 to-transparent"></div>
                    </div>
                    <div className="relative z-10 p-8 md:p-16 flex flex-col justify-end min-h-[450px] md:min-h-[550px] h-full">
                        <div className="mb-4">
                            <span className="px-3 py-1 bg-indigo-600 text-white text-xs font-bold uppercase tracking-wider rounded-md">{featuredPost.category}</span>
                        </div>
                        <h2 className="text-3xl md:text-5xl font-bold text-white mb-4 max-w-4xl leading-tight">{featuredPost.title}</h2>
                        <p className="text-lg text-gray-300 max-w-2xl mb-8 leading-relaxed">{featuredPost.excerpt}</p>
                        <div className="flex items-center gap-6 text-sm font-medium text-gray-400">
                            <span className="flex items-center gap-2"><Calendar className="w-4 h-4"/> {featuredPost.date}</span>
                            <span className="flex items-center gap-2"><Clock className="w-4 h-4"/> {featuredPost.readTime}</span>
                        </div>
                    </div>
                </motion.div>

                {/* Post Grid */}
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {posts.map((post, i) => (
                        <motion.div 
                            key={post.id}
                            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: i * 0.1 }}
                            className="bg-white rounded-3xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-xl transition-all group cursor-pointer"
                        >
                            <div className="h-48 overflow-hidden relative">
                                <img src={post.image} alt={post.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                                <div className="absolute top-4 left-4">
                                    <span className="px-3 py-1 bg-white/90 backdrop-blur border border-gray-100 text-gray-900 text-[10px] font-black uppercase tracking-wider rounded-md shadow-sm">{post.category}</span>
                                </div>
                            </div>
                            <div className="p-6">
                                <h3 className="text-xl font-bold text-gray-900 mb-4 group-hover:text-indigo-600 transition-colors leading-tight">{post.title}</h3>
                                <div className="flex items-center justify-between text-xs font-bold text-gray-500 mb-6">
                                    <span className="flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5"/> {post.date}</span>
                                    <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5"/> {post.readTime}</span>
                                </div>
                                <div className="flex items-center text-sm font-bold text-indigo-600 border-t border-gray-50 pt-4">
                                    Read Article <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>

            </div>
        </div>
    );
};

export default Blog;

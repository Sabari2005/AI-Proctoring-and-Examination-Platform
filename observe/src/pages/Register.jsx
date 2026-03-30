import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useBackend } from '../contexts/BackendContext';

const Register = () => {

    const { BACKEND_URL } = useBackend()
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        fullName: '',
        email: '',
        organization: '',
        password: ''
    })

    const handleChange = (e) => {
        const { name, value } = e.target
        setFormData((prev) => ({ ...prev, [name]: value }))
    }

    const handleRegister = async (e) => {
        e.preventDefault()

        const fullName = formData.fullName.trim()
        const email = formData.email.trim()
        const organization = formData.organization.trim()
        const password = formData.password.trim()

        // -------- Validation --------

        if (!fullName) {
            alert("Full name is required")
            return
        }

        if (!email) {
            alert("Email is required")
            return
        }

        if (!organization) {
            alert("Organization is required")
            return
        }

        if (!password) {
            alert("Password is required")
            return
        }

        if (password.length < 6) {
            alert("Password must be at least 6 characters")
            return
        }

        try {

            const response = await fetch(`${BACKEND_URL}/auth/register`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    full_name: fullName,
                    email: email,
                    organization: organization,
                    password: password
                })
            })

            const data = await response.json()

            if (!response.ok) {
                alert(data.message || "Registration failed")
                return
            }

            // Save candidate id
            localStorage.setItem("candidate_id", data.candidate_id)
            localStorage.setItem("access_token", data.access_token)

            // Redirect based on onboarding progress
            if (data.onboarding_step < 4) {
                navigate("/onboarding")
            } else {
                navigate("/dashboard")
            }

        } catch (error) {

            console.error("Registration error:", error)
            alert("Server connection failed")

        }
    }

    return (
        <div className="min-h-screen bg-white flex flex-col items-center justify-center text-center px-6 py-20">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4 }}
                className="w-full max-w-md p-8 rounded-3xl border border-gray-100 shadow-xl bg-white"
            >
                <h1 className="text-3xl font-bold tracking-tight text-gray-900 mb-2">Create an account</h1>
                <p className="text-gray-500 mb-8">Get started with Observe today</p>

                <form className="flex flex-col gap-4 text-left" onSubmit={handleRegister}>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 ml-1">Full Name</label>
                        <input name="fullName" value={formData.fullName} onChange={handleChange} type="text" placeholder="John Doe" className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 ml-1">Work Email</label>
                        <input name="email" value={formData.email} onChange={handleChange} type="email" placeholder="john@university.edu" className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 ml-1">Organization</label>
                        <input name="organization" value={formData.organization} onChange={handleChange} type="text" placeholder="University Name" className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 ml-1">Password</label>
                        <input name="password" value={formData.password} onChange={handleChange} type="password" placeholder="••••••••" className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900" />
                    </div>
                    <button type="submit" className="w-full px-4 py-3 rounded-xl bg-gray-900 text-white font-semibold hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 mt-4">
                        Create Account
                    </button>
                </form>

                <div className="my-6 flex items-center gap-4">
                    <div className="h-px bg-gray-200 flex-1"></div>
                    <span className="text-sm font-medium text-gray-400">OR</span>
                    <div className="h-px bg-gray-200 flex-1"></div>
                </div>

                <button className="w-full px-4 py-3 rounded-xl bg-white border border-gray-200 text-gray-700 font-semibold hover:bg-gray-50 transition-colors flex items-center justify-center gap-3 shadow-sm hover:shadow-md">
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                    </svg>
                    Continue with Google
                </button>                <p className="text-sm text-gray-500 mt-8">
                    Already have an account? <a href="/login" className="font-semibold text-gray-900 hover:underline">Sign in</a>
                </p>
            </motion.div>
        </div>
    );
};

export default Register;

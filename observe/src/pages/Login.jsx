import React, { useState } from 'react';
import { motion as Motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useBackend } from '../contexts/BackendContext';

const Login = () => {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const navigate = useNavigate()
    const { BACKEND_URL } = useBackend()

    const handleLogin = async (e) => {
        e.preventDefault()

        const trimmedEmail = email.trim()
        const trimmedPassword = password.trim()

        if (!trimmedEmail || !trimmedPassword) {
            alert('Please enter both email and password')
            return
        }

        try {
            setIsSubmitting(true)

            const response = await fetch(`${BACKEND_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: trimmedEmail,
                    password: trimmedPassword
                })
            })

            const data = await response.json().catch(() => ({}))

            if (!response.ok) {
                alert(data.detail || data.message || 'Login failed')
                return
            }

            localStorage.setItem('candidate_id', String(data.candidate_id))
            localStorage.setItem('access_token', data.access_token)

            if ((data.onboarding_step ?? 0) >= 4) {
                navigate('/dashboard')
            } else {
                navigate('/onboarding')
            }
        } catch (error) {
            console.error('Login error:', error)
            alert('Unable to connect to server')
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <div className="min-h-screen bg-white flex flex-col items-center justify-center text-center px-6">
            <Motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4 }}
                className="w-full max-w-md p-8 rounded-3xl border border-gray-100 shadow-xl bg-white"
            >
                <h1 className="text-3xl font-bold tracking-tight text-gray-900 mb-2">Welcome back</h1>
                <p className="text-gray-500 mb-8">Sign in to your Observe account</p>

                <form className="flex flex-col gap-4" onSubmit={handleLogin}>
                    <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="Email address" className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900" />
                    <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900" />
                    <div className="flex justify-end">
                        <a href="#" className="text-sm font-medium text-gray-500 hover:text-gray-900">Forgot password?</a>
                    </div>
                    <button disabled={isSubmitting} type="submit" className="w-full px-4 py-3 rounded-xl bg-gray-900 text-white font-semibold hover:bg-gray-800 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-gray-900/20 mt-2 disabled:opacity-70 disabled:cursor-not-allowed">
                        {isSubmitting ? 'Signing In...' : 'Sign In'}
                    </button>
                </form>

                <p className="text-sm text-gray-500 mt-8">
                    Don't have an account? <a href="/register" className="font-semibold text-gray-900 hover:underline">Sign up</a>
                </p>
            </Motion.div>
        </div>
    );
};

export default Login;

import React, { useState, useEffect } from 'react';
import { motion as Motion, AnimatePresence } from 'framer-motion';
import {
    User, ShieldCheck, GraduationCap, Link as LinkIcon,
    ArrowRight, ArrowLeft, Check, UploadCloud, ChevronRight,
    Sparkles, Globe2, Code2, Network
} from 'lucide-react';
import { useNavigate, Link } from 'react-router-dom';
import { useBackend } from '../contexts/BackendContext';
const steps = [
    {
        id: "account",
        title: "Account Setup",
        desc: "Secure your credentials",
        icon: User,
        illustration: (
            <div className="relative w-full h-full flex items-center justify-center p-8">
                <Motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 50, repeat: Infinity, ease: "linear" }}
                    className="absolute inset-0 border-[40px] border-white/5 rounded-full"
                />
                <Motion.div
                    animate={{ rotate: -360 }}
                    transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
                    className="absolute inset-10 border-[30px] border-white/5 rounded-full border-dashed"
                />
                <div className="relative z-10 w-full max-w-sm aspect-square bg-gradient-to-br from-indigo-500/20 to-purple-600/20 backdrop-blur-2xl rounded-[3rem] border border-white/20 shadow-2xl flex flex-col items-center justify-center p-10 overflow-hidden group">
                    <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                    <Motion.div
                        animate={{ y: [0, -10, 0] }}
                        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                    >
                        <ShieldCheck className="w-24 h-24 text-white mb-6 drop-shadow-2xl" />
                    </Motion.div>
                    <h3 className="text-2xl font-bold text-white mb-2 text-center">Military-Grade Security</h3>
                    <p className="text-indigo-100 text-center text-sm font-medium">Your data is locked within our proprietary zero-knowledge encryption vault.</p>
                </div>
            </div>
        )
    },
    {
        id: "identity",
        title: "Identity Check",
        desc: "Global verification",
        icon: ShieldCheck,
        illustration: (
            <div className="relative w-full h-full flex items-center justify-center p-8">
                <Motion.div
                    animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.6, 0.3] }}
                    transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
                    className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-blue-500/20 via-transparent to-transparent"
                />
                <div className="relative z-10 w-full max-w-sm aspect-square bg-gradient-to-br from-blue-500/20 to-cyan-600/20 backdrop-blur-2xl rounded-[3rem] border border-white/20 shadow-2xl flex flex-col items-center justify-center p-10 overflow-hidden group">
                    <Motion.div
                        animate={{ rotateY: 360 }}
                        transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
                    >
                        <Globe2 className="w-24 h-24 text-white mb-6 drop-shadow-2xl" />
                    </Motion.div>
                    <h3 className="text-2xl font-bold text-white mb-2 text-center">Global ID Network</h3>
                    <p className="text-blue-100 text-center text-sm font-medium">We instantly cross-reference over 14,000 global ID types in milliseconds.</p>
                </div>
            </div>
        )
    },
    {
        id: "profile",
        title: "Experience",
        desc: "Professional history",
        icon: GraduationCap,
        illustration: (
            <div className="relative w-full h-full flex items-center justify-center p-8">
                <div className="absolute inset-0 opacity-20 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMiIgY3k9IjIiIHI9IjIiIGZpbGw9IiNmZmZmZmYiLz48L3N2Zz4=')] [background-size:30px_30px]"></div>
                <div className="relative z-10 w-full max-w-sm aspect-square bg-gradient-to-br from-emerald-500/20 to-teal-600/20 backdrop-blur-2xl rounded-[3rem] border border-white/20 shadow-2xl flex flex-col items-center justify-center p-10 overflow-hidden group">
                    <Motion.div
                        animate={{ y: [0, -15, 0], scale: [1, 1.05, 1] }}
                        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                    >
                        <Network className="w-24 h-24 text-white mb-6 drop-shadow-2xl" />
                    </Motion.div>
                    <h3 className="text-2xl font-bold text-white mb-2 text-center">Neural Matching</h3>
                    <p className="text-emerald-100 text-center text-sm font-medium">Our AI maps your unique skills precisely to enterprise technical requirements.</p>
                </div>
            </div>
        )
    },
    {
        id: "links",
        title: "Portfolio",
        desc: "Technical footprints",
        icon: LinkIcon,
        illustration: (
            <div className="relative w-full h-full flex items-center justify-center p-8">
                <Motion.div
                    animate={{ opacity: [0.1, 0.3, 0.1] }}
                    transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                    className="absolute divide-y divide-white/5 w-full h-full flex flex-col"
                >
                    {[...Array(20)].map((_, i) => <div key={i} className="flex-1 border-b border-white/5"></div>)}
                </Motion.div>
                <div className="relative z-10 w-full max-w-sm aspect-square bg-gradient-to-br from-fuchsia-500/20 to-pink-600/20 backdrop-blur-2xl rounded-[3rem] border border-white/20 shadow-2xl flex flex-col items-center justify-center p-10 overflow-hidden group">
                    <Motion.div
                        animate={{ rotate: [-5, 5, -5] }}
                        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                    >
                        <Code2 className="w-24 h-24 text-white mb-6 drop-shadow-2xl" />
                    </Motion.div>
                    <h3 className="text-2xl font-bold text-white mb-2 text-center">Code Analysis</h3>
                    <p className="text-fuchsia-100 text-center text-sm font-medium">We deep-scan your repositories to validate architecture and commit quality automatically.</p>
                </div>
            </div>
        )
    }
];

const formVariants = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: { staggerChildren: 0.1, delayChildren: 0.1 }
    },
    exit: { opacity: 0, transition: { duration: 0.2 } }
};

const itemVariants = {
    hidden: { opacity: 0, x: 20, filter: "blur(4px)" },
    show: {
        opacity: 1,
        x: 0,
        filter: "blur(0px)",
        transition: { type: "spring", stiffness: 300, damping: 24 }
    }
};

const Onboarding = () => {
    const [currentStep, setCurrentStep] = useState(0)
    const [candidateData, setCandidateData] = useState({})
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [formData, setFormData] = useState({
        mobile_no: '',
        country: '',
        timezone: '',
        id_type: '',
        id_number: '',
        photo: null,
        aadhaar: null,
        education_level: '',
        university: '',
        specialization: '',
        graduation_year: '',
        years_of_experience: '',
        skills: '',
        linkedin: '',
        github: '',
        website: '',
        resume: null
    })
    const navigate = useNavigate()
    const { BACKEND_URL } = useBackend()   
    useEffect(() => {

        const candidateId = localStorage.getItem("candidate_id")

        if (!candidateId) return

        fetch(`${BACKEND_URL}/candidate/profile/${candidateId}`)
            .then(res => res.json())
            .then(data => {
                setCandidateData(data)

                setFormData((prev) => ({
                    ...prev,
                    mobile_no: data.mobile_no || '',
                    country: data.country || '',
                    timezone: data.timezone || ''
                }))

                if (data.onboarding_step !== undefined) {
                    if (data.onboarding_step >= steps.length) {
                        navigate('/dashboard')
                    } else {
                        setCurrentStep(data.onboarding_step)
                    }
                }

            })
            .catch(err => console.error(err))

    }, [BACKEND_URL, navigate])

    const updateFormField = (field, value) => {
        setFormData((prev) => ({ ...prev, [field]: value }))
    }

    const submitCurrentStep = async () => {
        const candidateId = Number(localStorage.getItem("candidate_id"))

        if (!candidateId) {
            alert("Candidate session not found. Please register again.")
            return false
        }

        if (currentStep === 0) {
            if (!formData.mobile_no.trim() || !formData.country.trim() || !formData.timezone.trim()) {
                alert("Please fill mobile number, country and timezone")
                return false
            }

            const response = await fetch(`${BACKEND_URL}/candidate/account`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    candidate_id: candidateId,
                    mobile_no: formData.mobile_no.trim(),
                    country: formData.country.trim(),
                    timezone: formData.timezone.trim()
                })
            })

            if (!response.ok) {
                const data = await response.json().catch(() => ({}))
                alert(data.error || data.message || "Failed to save account details")
                return false
            }
        }

        if (currentStep === 1) {
            if (!formData.id_type.trim() || !formData.id_number.trim() || !formData.photo || !formData.aadhaar) {
                alert("Please provide ID type, ID number, photo, and ID document")
                return false
            }

            const payload = new FormData()
            payload.append("candidate_id", String(candidateId))
            payload.append("id_type", formData.id_type.trim())
            payload.append("id_number", formData.id_number.trim())
            payload.append("photo", formData.photo)
            payload.append("aadhaar", formData.aadhaar)

            const response = await fetch(`${BACKEND_URL}/candidate/identity`, {
                method: "POST",
                body: payload
            })

            if (!response.ok) {
                const data = await response.json().catch(() => ({}))
                alert(data.error || data.message || "Failed to save identity details")
                return false
            }
        }

        if (currentStep === 2) {
            if (!formData.education_level || !formData.university.trim() || !formData.specialization.trim() || !formData.graduation_year || !formData.years_of_experience) {
                alert("Please complete all profile fields")
                return false
            }

            const skills = formData.skills
                .split(',')
                .map((skill) => skill.trim())
                .filter(Boolean)

            if (skills.length === 0) {
                alert("Please enter at least one skill")
                return false
            }

            const response = await fetch(`${BACKEND_URL}/candidate/profile`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    candidate_id: candidateId,
                    education_level: formData.education_level,
                    university: formData.university.trim(),
                    specialization: formData.specialization.trim(),
                    graduation_year: Number(formData.graduation_year),
                    years_of_experience: Number(formData.years_of_experience),
                    skills
                })
            })

            if (!response.ok) {
                const data = await response.json().catch(() => ({}))
                alert(data.error || data.message || "Failed to save profile details")
                return false
            }
        }

        if (currentStep === 3) {
            if (!formData.linkedin.trim() || !formData.github.trim() || !formData.resume) {
                alert("Please provide LinkedIn, GitHub and resume")
                return false
            }

            const payload = new FormData()
            payload.append("candidate_id", String(candidateId))
            payload.append("linkedin", formData.linkedin.trim())
            payload.append("github", formData.github.trim())
            payload.append("website", formData.website.trim())
            payload.append("resume", formData.resume)

            const response = await fetch(`${BACKEND_URL}/candidate/links`, {
                method: "POST",
                body: payload
            })

            if (!response.ok) {
                const data = await response.json().catch(() => ({}))
                alert(data.error || data.message || "Failed to save links")
                return false
            }
        }

        return true
    }

    const handleNext = async () => {
        setIsSubmitting(true)
        const ok = await submitCurrentStep()
        setIsSubmitting(false)

        if (!ok) {
            return
        }

        if (currentStep < steps.length - 1) {
            setCurrentStep(prev => prev + 1)
        } else {
            navigate('/dashboard')
        }
    }

    const handleBack = () => {
        if (currentStep > 0) {
            setCurrentStep(prev => prev - 1);
        }
    };

    return (
        <div className="flex flex-col md:flex-row min-h-screen bg-white font-sans text-gray-900 overflow-hidden selection:bg-indigo-500/30">

            {/* Left Presentation Pane (Dynamic Illustration Area) */}
            <div className="hidden md:flex md:w-[45%] lg:w-[40%] bg-gray-950 relative flex-col justify-between overflow-hidden">
                {/* Dynamic gradient blob based on step */}
                <Motion.div
                    className="absolute inset-0 opacity-40 mix-blend-screen pointer-events-none"
                    animate={{
                        background: currentStep === 0 ? 'radial-gradient(circle at 50% 50%, rgba(99, 102, 241, 0.4) 0%, transparent 70%)' :
                            currentStep === 1 ? 'radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.4) 0%, transparent 70%)' :
                                currentStep === 2 ? 'radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.4) 0%, transparent 70%)' :
                                    'radial-gradient(circle at 50% 50%, rgba(217, 70, 239, 0.4) 0%, transparent 70%)'
                    }}
                    transition={{ duration: 1 }}
                />

                <div className="p-10 relative z-10">
                    <Link to="/" className="inline-block hover:opacity-80 transition-opacity">
                        {/* White logo for dark background */}
                        <img src="/logo.svg" alt="Observe Logo" className="h-[28px] sm:h-[32px] md:h-24 filter invert brightness-0" />
                    </Link>
                </div>

                <div className="flex-grow flex items-center justify-center relative z-10">
                    <AnimatePresence mode="wait">
                        <Motion.div
                            key={currentStep}
                            initial={{ opacity: 0, scale: 0.9, rotateY: -20 }}
                            animate={{ opacity: 1, scale: 1, rotateY: 0 }}
                            exit={{ opacity: 0, scale: 1.1, rotateY: 20 }}
                            transition={{ duration: 0.5, ease: "easeInOut" }}
                            className="w-full h-full"
                        >
                            {steps[currentStep].illustration}
                        </Motion.div>
                    </AnimatePresence>
                </div>

                <div className="p-10 relative z-10">
                    <div className="flex items-center gap-3 text-white/50 text-sm font-medium">
                        <Sparkles className="w-4 h-4" /> Powering next-gen recruitment
                    </div>
                </div>
            </div>

            {/* Right Form Pane */}
            <div className="flex-grow flex flex-col relative bg-[#F9FAFB] md:rounded-l-[2.5rem] md:-ml-6 z-20 shadow-[-20px_0_40px_rgba(0,0,0,0.1)] overflow-y-auto scrollbar-hide">
                <div className="max-w-3xl w-full mx-auto p-8 sm:p-12 lg:p-16 flex flex-col min-h-screen justify-between">

                    <div>
                        {/* Stepper Header */}
                        <div className="flex items-center gap-3 sm:gap-6 mb-12 overflow-x-auto pb-4 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
                            {steps.map((step, idx) => {
                                const Icon = step.icon;
                                const isActive = idx === currentStep;
                                const isPast = idx < currentStep;

                                return (
                                    <React.Fragment key={idx}>
                                        <div className="flex items-center gap-3 shrink-0">
                                            <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center font-bold transition-all duration-300 ${isActive ? 'bg-emerald-400 text-white shadow-lg shadow-emerald-200 scale-110' :
                                                isPast ? 'bg-gray-900 text-white' : 'bg-white border border-gray-200 text-gray-400'
                                                }`}>
                                                {isPast ? <Check className="w-4 h-4 sm:w-5 sm:h-5" /> : <Icon className="w-4 h-4 sm:w-5 sm:h-5" />}
                                            </div>
                                            <div className="hidden sm:block">
                                                <div className={`text-xs font-bold uppercase tracking-wider ${isActive ? 'text-emerald-500' : isPast ? 'text-gray-900' : 'text-gray-400'}`}>Step {idx + 1}</div>
                                                <div className={`text-sm font-medium ${isActive || isPast ? 'text-gray-900' : 'text-gray-400'}`}>{step.title}</div>
                                            </div>
                                        </div>
                                        {idx < steps.length - 1 && (
                                            <div className="shrink-0 w-8 sm:w-12 h-[2px] rounded-full bg-gray-200 relative overflow-hidden">
                                                <Motion.div
                                                    className="absolute inset-0 bg-gray-900 origin-left"
                                                    initial={{ scaleX: 0 }}
                                                    animate={{ scaleX: isPast ? 1 : 0 }}
                                                    transition={{ duration: 0.4 }}
                                                />
                                            </div>
                                        )}
                                    </React.Fragment>
                                );
                            })}
                        </div>

                        {/* Title Context */}
                        <AnimatePresence mode="wait">
                            <Motion.div
                                key={`title-${currentStep}`}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                transition={{ duration: 0.3 }}
                                className="mb-10"
                            >
                                <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-gray-900 mb-3">{steps[currentStep].title}</h1>
                                <p className="text-gray-500 text-base sm:text-lg">{steps[currentStep].desc}. Please fill in the details below to proceed with your application securely.</p>
                            </Motion.div>
                        </AnimatePresence>

                        {/* Form Area with Glassmorphism / Elevated fields */}
                        <AnimatePresence mode="wait">
                            <Motion.div
                                key={currentStep}
                                variants={formVariants}
                                initial="hidden"
                                animate="show"
                                exit="exit"
                                className="w-full"
                            >
                                {currentStep === 0 && <AccountStep candidateData={candidateData} formData={formData} onChange={updateFormField} />}
                                {currentStep === 1 && <IdentityStep formData={formData} onChange={updateFormField} />}
                                {currentStep === 2 && <ProfileStep formData={formData} onChange={updateFormField} />}
                                {currentStep === 3 && <LinksStep formData={formData} onChange={updateFormField} />}
                            </Motion.div>
                        </AnimatePresence>
                    </div>

                    {/* Navigation Buttons */}
                    <div className="mt-16 pt-8 border-t border-gray-200 flex items-center justify-between">
                        <button
                            onClick={handleBack}
                            className={`px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all duration-300 ${currentStep === 0 ? 'opacity-0 pointer-events-none' : 'text-gray-500 hover:bg-white hover:text-gray-900 hover:shadow-sm border border-transparent hover:border-gray-200 hover:-translate-x-1'}`}
                            disabled={currentStep === 0}
                        >
                            <ArrowLeft className="w-5 h-5" /> Back
                        </button>

                        <button
                            onClick={handleNext}
                            disabled={isSubmitting}
                            className="group relative px-8 py-4 bg-gray-900 text-white rounded-xl font-bold flex items-center gap-3 overflow-hidden transition-all duration-300 hover:scale-105 hover:bg-gray-800 hover:shadow-xl hover:shadow-gray-900/20"
                        >
                            <span className="relative z-10 flex items-center gap-2">
                                {isSubmitting ? 'Saving...' : (currentStep === steps.length - 1 ? 'Complete Onboarding' : 'Continue')}
                                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                            </span>
                        </button>
                    </div>

                </div>
            </div>
        </div>
    );
};

/* --- Glassmorphism / Soft Form Elements --- */

const CustomInput = ({ label, type = "text", placeholder, value, disabled, onChange }) => (
    <Motion.div variants={itemVariants} className="space-y-2 mb-6 w-full group">
        <label className="block text-[13px] font-bold text-gray-700 uppercase tracking-wider ml-1">
            {label}
        </label>

        <input
            type={type}
            placeholder={placeholder}
            value={value || ""}
            disabled={disabled}
            onChange={onChange}
            className="w-full px-5 py-4 rounded-2xl border-2 border-white bg-white/60 backdrop-blur-md shadow-sm focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all text-[15px] font-medium text-gray-900"
        />
    </Motion.div>
)

const CustomSelect = ({ label, options, value, onChange }) => (
    <Motion.div variants={itemVariants} className="space-y-2 mb-6 w-full">
        <label className="block text-[13px] font-bold text-gray-700 uppercase tracking-wider ml-1">
            {label}
        </label>
        <div className="relative group">
            <select value={value} onChange={onChange} className="w-full px-5 py-4 rounded-2xl border-2 border-white bg-white/60 backdrop-blur-md shadow-[0_2px_10px_rgba(0,0,0,0.02)] focus:outline-none focus:border-indigo-500 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 transition-all text-[15px] font-medium text-gray-900 appearance-none cursor-pointer hover:shadow-[0_4px_20px_rgba(0,0,0,0.04)]">
                {options.map((opt, i) => (
                    <option key={i} value={opt.value} className="text-gray-900">{opt.label}</option>
                ))}
            </select>
            <div className="absolute right-5 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400 group-hover:text-indigo-500 transition-colors">
                <ChevronRight className="w-5 h-5 rotate-90" />
            </div>
        </div>
    </Motion.div>
);

const AccountStep = ({ candidateData, formData, onChange }) => (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
        <CustomInput
            label="Full Name"
            value={candidateData.full_name}
            disabled
        />
        <CustomInput
            label="Email Address"
            value={candidateData.email}
            disabled
        />
        <CustomInput
            label="Mobile Number"
            type='tel'
            placeholder="+1 (555) 000-0000"
            value={formData.mobile_no}
            onChange={(e) => onChange('mobile_no', e.target.value)}
        />
        <div className="sm:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-x-6">
            <CustomSelect
                label="Country"
                value={formData.country}
                onChange={(e) => onChange('country', e.target.value)}
                options={[
                    { value: '', label: 'Select Country...' },
                    { value: 'United States', label: 'United States' },
                    { value: 'United Kingdom', label: 'United Kingdom' },
                    { value: 'Canada', label: 'Canada' },
                    { value: 'Australia', label: 'Australia' },
                    { value: 'India', label: 'India' }
                ]}
            />
            <CustomSelect
                label="Timezone"
                value={formData.timezone}
                onChange={(e) => onChange('timezone', e.target.value)}
                options={[
                    { value: '', label: 'Select Timezone...' },
                    { value: 'Eastern Time (ET)', label: 'Eastern Time (ET)' },
                    { value: 'Pacific Time (PT)', label: 'Pacific Time (PT)' },
                    { value: 'Greenwich Mean Time (GMT)', label: 'Greenwich Mean Time (GMT)' },
                    { value: 'Indian Standard Time (IST)', label: 'Indian Standard Time (IST)' }
                ]}
            />
        </div>
    </div>
);

const IdentityStep = ({ formData, onChange }) => (
    <div className="flex flex-col gap-6">
        <div className="flex flex-col sm:flex-row gap-6 items-start">
            <Motion.div variants={itemVariants} className="flex-shrink-0 w-full sm:w-auto flex flex-col items-center">
                <label className="block text-[13px] font-bold text-gray-700 uppercase tracking-wider ml-1 mb-2 self-start sm:self-auto">Profile Photo</label>
                <label className="w-full sm:w-36 h-36 rounded-3xl border-2 border-dashed border-indigo-200 bg-indigo-50/50 backdrop-blur-sm flex flex-col items-center justify-center cursor-pointer hover:border-indigo-500 hover:bg-white hover:shadow-[0_8px_30px_rgba(99,102,241,0.1)] transition-all group overflow-hidden relative">
                    <User className="w-10 h-10 text-indigo-300 group-hover:scale-110 group-hover:text-indigo-600 transition-all duration-300 relative z-10" />
                    <span className="text-xs font-semibold text-indigo-700 mt-2 px-3 text-center">{formData.photo ? formData.photo.name : 'Upload photo'}</span>
                    <div className="absolute inset-0 bg-gradient-to-t from-indigo-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    <input
                        type="file"
                        className="hidden"
                        accept="image/*"
                        onChange={(e) => onChange('photo', e.target.files?.[0] || null)}
                    />
                </label>
            </Motion.div>

            <div className="flex-grow grid grid-cols-1 w-full mt-2 sm:mt-0">
                <CustomSelect
                    label="Government ID Type"
                    value={formData.id_type}
                    onChange={(e) => onChange('id_type', e.target.value)}
                    options={[
                        { value: '', label: 'Select ID Type...' },
                        { value: 'Passport', label: 'Passport' },
                        { value: "Driver's License", label: "Driver's License" },
                        { value: 'National ID Card', label: 'National ID Card' },
                        { value: 'State ID', label: 'State ID' }
                    ]}
                />
                <CustomInput
                    label="Government ID Number"
                    placeholder="e.g. D12345678"
                    value={formData.id_number}
                    onChange={(e) => onChange('id_number', e.target.value)}
                />
            </div>
        </div>

        <Motion.div variants={itemVariants} className="w-full pt-4">
            <label className="block text-[13px] font-bold text-gray-700 uppercase tracking-wider ml-1 mb-2">Upload ID Document (Front & Back)</label>
            <label className="w-full h-48 rounded-[2rem] border-2 border-dashed border-indigo-200 bg-white/60 backdrop-blur-md shadow-[0_2px_10px_rgba(0,0,0,0.02)] flex flex-col items-center justify-center cursor-pointer hover:border-indigo-500 hover:bg-white hover:shadow-[0_8px_30px_rgba(99,102,241,0.1)] transition-all group overflow-hidden relative">
                <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center mb-4 group-hover:-translate-y-2 transition-transform duration-300 group-hover:bg-indigo-100 relative z-10">
                    <UploadCloud className="w-7 h-7 text-indigo-500 group-hover:text-indigo-700 transition-colors" />
                </div>
                <span className="text-[16px] text-gray-800 font-bold group-hover:text-indigo-900 transition-colors relative z-10">Drag and drop your document here</span>
                <span className="text-[13px] text-gray-500 mt-1 font-medium relative z-10">{formData.aadhaar ? formData.aadhaar.name : 'Requires PNG, JPG, or PDF (max. 10MB)'}</span>
                <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <input
                    type="file"
                    className="hidden"
                    accept="image/*,application/pdf"
                    onChange={(e) => onChange('aadhaar', e.target.files?.[0] || null)}
                />
            </label>
        </Motion.div>
    </div>
);

const ProfileStep = ({ formData, onChange }) => (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
        <CustomSelect
            label="Education Level"
            value={formData.education_level}
            onChange={(e) => onChange('education_level', e.target.value)}
            options={[
                { value: '', label: 'Highest Degree Obtained...' },
                { value: "Bachelor's Degree", label: "Bachelor's Degree" },
                { value: "Master's Degree", label: "Master's Degree" },
                { value: 'Ph.D.', label: 'Ph.D.' },
                { value: 'Associate Degree', label: 'Associate Degree' },
                { value: 'Other', label: 'Other' }
            ]}
        />
        <CustomInput
            label="University / College"
            placeholder="e.g. MIT, Stanford"
            value={formData.university}
            onChange={(e) => onChange('university', e.target.value)}
        />
        <CustomInput
            label="Graduation Year"
            type="number"
            placeholder="YYYY"
            value={formData.graduation_year}
            onChange={(e) => onChange('graduation_year', e.target.value)}
        />
        <CustomInput
            label="Specialization / Major"
            placeholder="e.g. Computer Science"
            value={formData.specialization}
            onChange={(e) => onChange('specialization', e.target.value)}
        />
        <CustomInput
            label="Years of Experience"
            type="number"
            placeholder="e.g. 5"
            value={formData.years_of_experience}
            onChange={(e) => onChange('years_of_experience', e.target.value)}
        />
        <CustomInput
            label="Technical Skills"
            placeholder="React, Node.js, Python..."
            value={formData.skills}
            onChange={(e) => onChange('skills', e.target.value)}
        />
    </div>
);

const LinksStep = ({ formData, onChange }) => (
    <div className="flex flex-col gap-6">
        <Motion.div variants={itemVariants} className="w-full">
            <label className="block text-[13px] font-bold text-gray-700 uppercase tracking-wider ml-1 mb-2">Upload Resume</label>
            <label className="w-full h-32 rounded-[1.5rem] border-2 border-dashed border-gray-200 bg-white/60 backdrop-blur-md flex flex-col items-center justify-center cursor-pointer hover:border-gray-900 hover:bg-white hover:shadow-[0_4px_20px_rgba(0,0,0,0.06)] transition-all group relative overflow-hidden">
                <div className="flex items-center gap-3 relative z-10">
                    <div className="bg-gray-100 p-2 rounded-lg group-hover:bg-gray-200 transition-colors">
                        <UploadCloud className="w-5 h-5 text-gray-600 group-hover:text-gray-900 transition-colors" />
                    </div>
                    <span className="text-[15px] text-gray-700 font-bold group-hover:text-gray-900 transition-colors">{formData.resume ? formData.resume.name : 'Attach resume file'}</span>
                </div>
                <span className="text-[12px] text-gray-500 mt-2 font-medium relative z-10">PDF or DOCX (max. 10MB)</span>
                <input
                    type="file"
                    className="hidden"
                    accept="application/pdf,.doc,.docx"
                    onChange={(e) => onChange('resume', e.target.files?.[0] || null)}
                />
            </label>
        </Motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 pt-2">
            <Motion.div variants={itemVariants} className="space-y-2 mb-6 w-full">
                <label className="block text-[13px] font-bold text-gray-700 uppercase tracking-wider ml-1">LinkedIn Profile</label>
                <div className="flex rounded-2xl border-2 border-white bg-white/60 backdrop-blur-md shadow-[0_2px_10px_rgba(0,0,0,0.02)] focus-within:border-indigo-500 focus-within:ring-4 focus-within:ring-indigo-500/10 transition-all overflow-hidden group">
                    <span className="inline-flex items-center px-4 bg-gray-50/50 text-gray-500 text-[14px] font-medium border-r border-white group-focus-within:bg-indigo-50/50 group-focus-within:text-indigo-600 transition-colors">linkedin.com/in/</span>
                    <input type="text" value={formData.linkedin} onChange={(e) => onChange('linkedin', e.target.value)} placeholder="username" className="flex-1 min-w-0 w-full px-4 py-4 focus:outline-none focus:bg-white text-[15px] font-medium text-gray-900 bg-transparent" />
                </div>
            </Motion.div>

            <Motion.div variants={itemVariants} className="space-y-2 mb-6 w-full">
                <label className="block text-[13px] font-bold text-gray-700 uppercase tracking-wider ml-1">GitHub Profile</label>
                <div className="flex rounded-2xl border-2 border-white bg-white/60 backdrop-blur-md shadow-[0_2px_10px_rgba(0,0,0,0.02)] focus-within:border-indigo-500 focus-within:ring-4 focus-within:ring-indigo-500/10 transition-all overflow-hidden group">
                    <span className="inline-flex items-center px-4 bg-gray-50/50 text-gray-500 text-[14px] font-medium border-r border-white group-focus-within:bg-indigo-50/50 group-focus-within:text-indigo-600 transition-colors">github.com/</span>
                    <input type="text" value={formData.github} onChange={(e) => onChange('github', e.target.value)} placeholder="username" className="flex-1 min-w-0 w-full px-4 py-4 focus:outline-none focus:bg-white text-[15px] font-medium text-gray-900 bg-transparent" />
                </div>
            </Motion.div>

            <div className="sm:col-span-2">
                <CustomInput
                    label="Personal Website / Portfolio (Optional)"
                    placeholder="https://yourwebsite.com"
                    value={formData.website}
                    onChange={(e) => onChange('website', e.target.value)}
                />
            </div>
        </div>
    </div>
);

export default Onboarding;


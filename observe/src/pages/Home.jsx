import React from 'react';
import Hero from '../components/Hero';
import SocialProof from '../components/SocialProof';
import Features from '../components/Features';
import Security from '../components/Security';

const Home = () => {
    return (
        <main>
            <Hero />
            <SocialProof />
            <Features />
            <Security />
        </main>
    );
};

export default Home;

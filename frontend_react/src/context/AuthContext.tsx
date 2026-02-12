import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
    id: string;
    email: string;
    role: 'ceo' | 'professional' | 'secretary';
    niche_type?: 'dental' | 'crm_sales';
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (token: string, user: User) => void;
    logout: () => void;
    updateUser: (partial: Partial<User>) => void;
    isAuthenticated: boolean;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(localStorage.getItem('JWT_TOKEN'));
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const savedUser = localStorage.getItem('USER_PROFILE');
        if (savedUser && token) {
            try {
                setUser(JSON.parse(savedUser));
            } catch (e) {
                console.error("Error parsing user profile:", e);
                logout();
            }
        }
        setIsLoading(false);
    }, [token]);

    const login = (newToken: string, profile: User) => {
        localStorage.setItem('JWT_TOKEN', newToken);
        localStorage.setItem('USER_PROFILE', JSON.stringify(profile));
        setToken(newToken);
        setUser(profile);
    };

    const logout = () => {
        localStorage.removeItem('JWT_TOKEN');
        localStorage.removeItem('USER_PROFILE');
        setToken(null);
        setUser(null);
    };

    const updateUser = (partial: Partial<User>) => {
        setUser((prev) => {
            if (!prev) return prev;
            const next = { ...prev, ...partial };
            localStorage.setItem('USER_PROFILE', JSON.stringify(next));
            return next;
        });
    };

    return (
        <AuthContext.Provider value={{
            user,
            token,
            login,
            logout,
            updateUser,
            isAuthenticated: !!token,
            isLoading
        }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import api from '../api/axios';

interface User {
    id: string;
    email: string;
    role: 'ceo' | 'professional' | 'secretary' | 'setter' | 'closer';
    tenant_id?: number;
    niche_type?: 'dental' | 'crm_sales';
}

interface AuthContextType {
    user: User | null;
    token: string | null;        // Mantenido para compatibilidad, puede ser null si se usa solo cookie
    login: (token: string, user: User) => void;
    logout: () => Promise<void>;
    updateUser: (partial: Partial<User>) => void;
    isAuthenticated: boolean;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(localStorage.getItem('JWT_TOKEN'));
    const [isLoading, setIsLoading] = useState(true);

    // Nexus Security v7.6: verificar sesión activa al iniciar
    // Si hay cookie HttpOnly el backend responde 200 con el perfil
    useEffect(() => {
        const verifySession = async () => {
            setIsLoading(true);
            try {
                // Intentar recuperar perfil desde la cookie HttpOnly (withCredentials en axios)
                const response = await api.get('/auth/me');
                if (response.data) {
                    setUser(response.data);
                    // Si el login también retornó el token en body (transición dual), guardarlo
                    const storedToken = localStorage.getItem('JWT_TOKEN');
                    if (storedToken) setToken(storedToken);
                }
            } catch (error) {
                // 401 = sin sesión válida (cookie expirada o no existe)
                // Limpiar estado local
                localStorage.removeItem('JWT_TOKEN');
                localStorage.removeItem('USER_PROFILE');
                setToken(null);
                setUser(null);
            } finally {
                setIsLoading(false);
            }
        };

        verifySession();
        // Solo ejecutar al montar el componente
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const login = (newToken: string, profile: User) => {
        // Compatibilidad dual durante transición: guardar en localStorage Y confiar en cookie
        localStorage.setItem('JWT_TOKEN', newToken);
        localStorage.setItem('USER_PROFILE', JSON.stringify(profile));
        setToken(newToken);
        setUser(profile);
    };

    const logout = async () => {
        // Nexus Security v7.6: limpiar cookie HttpOnly desde el servidor
        try {
            await api.post('/auth/logout');
        } catch (e) {
            // Ignorar errores al hacer logout (ej: sin conexión)
            console.warn('[Auth] Error al hacer logout en servidor:', e);
        }
        // Limpiar estado local también
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
            isAuthenticated: !!user, // Nexus v7.6: basarse en el user, no solo en el token
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

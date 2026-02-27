import React, { createContext, useContext, useEffect, useRef, useState, ReactNode } from 'react';
import { io, Socket } from 'socket.io-client';
import { BACKEND_URL } from '../api/axios';
import { useAuth } from './AuthContext';

interface SocketContextType {
  socket: Socket | null;
  isConnected: boolean;
  connect: () => void;
  disconnect: () => void;
  subscribeToNotifications: (userId: string) => void;
  unsubscribeFromNotifications: (userId: string) => void;
}

const SocketContext = createContext<SocketContextType | undefined>(undefined);

interface SocketProviderProps {
  children: ReactNode;
  autoConnect?: boolean;
}

export const SocketProvider: React.FC<SocketProviderProps> = ({ 
  children, 
  autoConnect = true 
}) => {
  const { user } = useAuth();
  const socketRef = useRef<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const connect = () => {
    if (socketRef.current?.connected) {
      console.log('Socket already connected');
      return;
    }

    try {
      // Conectar al servidor Socket.IO
      socketRef.current = io(BACKEND_URL, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
      });

      // Eventos de conexión
      socketRef.current.on('connect', () => {
        console.log('Socket.IO connected:', socketRef.current?.id);
        setIsConnected(true);
        
        // Notificar que estamos conectados
        socketRef.current?.emit('notification_connected', {
          status: 'connected',
          timestamp: new Date().toISOString()
        });
      });

      socketRef.current.on('disconnect', (reason) => {
        console.log('Socket.IO disconnected:', reason);
        setIsConnected(false);
      });

      socketRef.current.on('connect_error', (error) => {
        console.error('Socket.IO connection error:', error);
        setIsConnected(false);
      });

      socketRef.current.on('reconnect', (attemptNumber) => {
        console.log('Socket.IO reconnected after', attemptNumber, 'attempts');
        setIsConnected(true);
        
        // Re-suscribir a notificaciones si hay usuario
        if (user?.id) {
          subscribeToNotifications(user.id);
        }
      });

      // Escuchar eventos de notificaciones
      socketRef.current.on('notification_connected', (data) => {
        console.log('Notification socket connected:', data);
      });

      socketRef.current.on('notification_subscribed', (data) => {
        console.log('Subscribed to notifications:', data);
      });

      socketRef.current.on('new_notification', (data) => {
        console.log('New notification received:', data);
        // Este evento será manejado por componentes específicos
        // que se suscriban a través de useSocketNotifications
      });

      socketRef.current.on('notification_count_update', (data) => {
        console.log('Notification count updated:', data);
        // Este evento será manejado por componentes específicos
      });

      socketRef.current.on('notification_marked_read', (data) => {
        console.log('Notification marked as read:', data);
      });

    } catch (error) {
      console.error('Error connecting Socket.IO:', error);
    }
  };

  const disconnect = () => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setIsConnected(false);
    }
  };

  const subscribeToNotifications = (userId: string) => {
    if (!socketRef.current?.connected) {
      console.warn('Socket not connected, cannot subscribe to notifications');
      return;
    }

    try {
      socketRef.current.emit('subscribe_notifications', { user_id: userId });
      console.log('Subscribing to notifications for user:', userId);
    } catch (error) {
      console.error('Error subscribing to notifications:', error);
    }
  };

  const unsubscribeFromNotifications = (userId: string) => {
    if (!socketRef.current?.connected) {
      return;
    }

    try {
      socketRef.current.emit('unsubscribe_notifications', { user_id: userId });
      console.log('Unsubscribing from notifications for user:', userId);
    } catch (error) {
      console.error('Error unsubscribing from notifications:', error);
    }
  };

  // Auto-conectar cuando hay usuario
  useEffect(() => {
    if (autoConnect && user?.id) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [user?.id, autoConnect]);

  // Auto-suscribir cuando se conecta y hay usuario
  useEffect(() => {
    if (isConnected && user?.id) {
      subscribeToNotifications(user.id);
    }
  }, [isConnected, user?.id]);

  const value: SocketContextType = {
    socket: socketRef.current,
    isConnected,
    connect,
    disconnect,
    subscribeToNotifications,
    unsubscribeFromNotifications,
  };

  return (
    <SocketContext.Provider value={value}>
      {children}
    </SocketContext.Provider>
  );
};

export const useSocket = (): SocketContextType => {
  const context = useContext(SocketContext);
  if (context === undefined) {
    throw new Error('useSocket must be used within a SocketProvider');
  }
  return context;
};

// Hook específico para notificaciones
export const useSocketNotifications = () => {
  const { socket, isConnected } = useSocket();
  const [notificationCount, setNotificationCount] = useState({
    total: 0,
    critical: 0,
    high: 0,
    medium: 0,
    low: 0
  });
  const [newNotifications, setNewNotifications] = useState<any[]>([]);

  useEffect(() => {
    if (!socket || !isConnected) {
      return;
    }

    // Escuchar actualizaciones de count
    const handleCountUpdate = (data: any) => {
      setNotificationCount(data);
      console.log('Notification count updated via socket:', data);
    };

    // Escuchar nuevas notificaciones
    const handleNewNotification = (data: any) => {
      setNewNotifications(prev => [data, ...prev.slice(0, 9)]); // Mantener solo las 10 más recientes
      console.log('New notification via socket:', data);
    };

    socket.on('notification_count_update', handleCountUpdate);
    socket.on('new_notification', handleNewNotification);

    // Solicitar count inicial
    socket.emit('get_notification_count', { user_id: 'current' });

    return () => {
      socket.off('notification_count_update', handleCountUpdate);
      socket.off('new_notification', handleNewNotification);
    };
  }, [socket, isConnected]);

  const markAsRead = (notificationId: string) => {
    if (!socket || !isConnected) {
      return;
    }

    socket.emit('mark_notification_read', {
      notification_id: notificationId,
      user_id: 'current'
    });
  };

  const refreshCount = () => {
    if (!socket || !isConnected) {
      return;
    }

    socket.emit('get_notification_count', { user_id: 'current' });
  };

  return {
    notificationCount,
    newNotifications,
    markAsRead,
    refreshCount,
    isConnected
  };
};
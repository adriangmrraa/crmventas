import React from 'react';
import { Bell } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import NotificationCenter from '../components/NotificationCenter';

export default function NotificationsView() {
    return (
        <div className="h-screen flex flex-col bg-gray-50 overflow-hidden">
            <div className="flex-none p-6 pb-0 max-w-6xl mx-auto w-full">
                <PageHeader
                    title="Centro de Notificaciones"
                    subtitle="Visualiza todas las alertas y eventos del sistema"
                    icon={<Bell size={22} />}
                />
            </div>
            <div className="flex-1 overflow-y-auto bg-gray-50/50 scrollbar-thin scrollbar-thumb-gray-200">
                <div className="p-6 max-w-6xl mx-auto pb-32">
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
                        {/* We use the existing NotificationCenter component but as a standalone full page view */}
                        <div className="p-4 bg-gray-50 border-b border-gray-200 flex justify-between items-center">
                            <h2 className="font-semibold text-gray-800">Todas las Notificaciones</h2>
                        </div>
                        <div className="hidden sm:block">
                            {/* Desktop Version: We can just render the component without the absolute positioning class */}
                            <div className="relative w-full">
                                <NotificationCenter
                                    onClose={() => { }}
                                    onNotificationRead={() => { }}
                                    onMarkAllRead={() => { }}
                                />
                            </div>
                        </div>
                        <div className="block sm:hidden relative min-h-[500px]">
                            {/* Mobile version */}
                            <NotificationCenter
                                onClose={() => { }}
                                onNotificationRead={() => { }}
                                onMarkAllRead={() => { }}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

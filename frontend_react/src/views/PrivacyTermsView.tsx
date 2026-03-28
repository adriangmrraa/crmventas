import { Shield, FileText, ChevronLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '../context/LanguageContext';

export default function PrivacyTermsView() {
    const navigate = useNavigate();
    const { t } = useTranslation();
    const appName = t('nav.app_name');

    const interpolate = (key: string) => t(key).replace(/{appName}/g, appName);

    return (
        <div className="min-h-screen bg-white/[0.02] py-12 px-6">
            <div className="max-w-3xl mx-auto space-y-8">
                <button
                    onClick={() => navigate('/login')}
                    className="flex items-center gap-2 text-white/40 hover:text-white transition-colors mb-4"
                >
                    <ChevronLeft size={20} /> {t('legal.back_button')}
                </button>

                <div className="text-center space-y-4">
                    <div className="w-16 h-16 bg-blue-500/10 text-blue-400 rounded-2xl flex items-center justify-center mx-auto mb-4">
                        <Shield size={32} />
                    </div>
                    <h1 className="text-3xl font-bold text-white">{interpolate('legal.center_title')}</h1>
                    <p className="text-white/40 text-lg">{t('legal.center_subtitle')}</p>
                </div>

                {/* Privacy Policy */}
                <section id="privacy" className="bg-white/[0.03] border border-white/[0.06] rounded-3xl p-8 space-y-6">
                    <div className="flex items-center gap-3 border-b border-white/[0.04] pb-4">
                        <Shield className="text-blue-500" size={24} />
                        <h2 className="text-2xl font-bold text-white">{t('privacy.title')}</h2>
                    </div>

                    <div className="prose prose-blue max-w-none text-white/50 space-y-4">
                        <p>{t('privacy.last_updated')}</p>

                        <h3 className="text-lg font-semibold text-white">{t('privacy.s1_title')}</h3>
                        <p>{interpolate('privacy.s1_body')}</p>

                        <h3 className="text-lg font-semibold text-white">{t('privacy.s2_title')}</h3>
                        <p>{t('privacy.s2_intro')}</p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li>{t('privacy.s2_item1')}</li>
                            <li>{t('privacy.s2_item2')}</li>
                            <li>{t('privacy.s2_item3')}</li>
                        </ul>

                        <h3 className="text-lg font-semibold text-white">{t('privacy.s3_title')}</h3>
                        <p>{interpolate('privacy.s3_body')}</p>
                    </div>
                </section>

                {/* Terms of Service */}
                <section id="terms" className="bg-white/[0.03] border border-white/[0.06] rounded-3xl p-8 space-y-6">
                    <div className="flex items-center gap-3 border-b border-white/[0.04] pb-4">
                        <FileText className="text-blue-500" size={24} />
                        <h2 className="text-2xl font-bold text-white">{t('terms.title')}</h2>
                    </div>

                    <div className="prose prose-blue max-w-none text-white/50 space-y-4">
                        <p>{interpolate('terms.intro')}</p>

                        <h3 className="text-lg font-semibold text-white">{t('terms.s1_title')}</h3>
                        <p>{interpolate('terms.s1_body')}</p>

                        <h3 className="text-lg font-semibold text-white">{t('terms.s2_title')}</h3>
                        <p>{interpolate('terms.s2_body')}</p>

                        <h3 className="text-lg font-semibold text-white">{t('terms.s3_title')}</h3>
                        <p>{interpolate('terms.s3_body')}</p>
                    </div>
                </section>

                <div className="text-center text-white/30 text-sm pt-8 border-t border-white/[0.06]">
                    {interpolate('legal.footer')}
                </div>
            </div>
        </div>
    );
}
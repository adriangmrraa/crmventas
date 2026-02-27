import React, { useState, useEffect } from 'react';
import { User, UserPlus, Loader2, Check, X, Users, Filter } from 'lucide-react';
import api from '../api/axios';
import { useTranslation } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import SellerBadge from './SellerBadge';

interface Seller {
  id: string;
  first_name: string;
  last_name: string;
  role: string;
  email: string;
  active_conversations?: number;
  conversion_rate?: number;
}

interface SellerSelectorProps {
  phone: string;
  currentSellerId?: string | null;
  currentSellerName?: string;
  currentSellerRole?: string;
  onSellerSelected: (sellerId: string, sellerName: string) => Promise<void>;
  onCancel?: () => void;
  showAssignToMe?: boolean;
  showAutoAssign?: boolean;
  className?: string;
}

const SellerSelector: React.FC<SellerSelectorProps> = ({
  phone,
  currentSellerId,
  currentSellerName,
  currentSellerRole,
  onSellerSelected,
  onCancel,
  showAssignToMe = true,
  showAutoAssign = true,
  className = ''
}) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [assigning, setAssigning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  useEffect(() => {
    fetchSellers();
  }, [roleFilter]);
  
  const fetchSellers = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params: any = {};
      if (roleFilter !== 'all') {
        params.role = roleFilter;
      }
      
      const response = await api.get('/admin/core/sellers/available', { params });
      
      if (response.data.success) {
        setSellers(response.data.sellers);
      } else {
        setError(response.data.message || t('sellers.error_fetching'));
      }
    } catch (err: any) {
      console.error('Error fetching sellers:', err);
      setError(err.response?.data?.detail || t('sellers.error_fetching'));
    } finally {
      setLoading(false);
    }
  };
  
  const handleAssignToSeller = async (sellerId: string, sellerName: string) => {
    try {
      setAssigning(sellerId);
      setError(null);
      
      await onSellerSelected(sellerId, sellerName);
    } catch (err: any) {
      console.error('Error assigning seller:', err);
      setError(err.response?.data?.detail || t('sellers.error_assigning'));
    } finally {
      setAssigning(null);
    }
  };
  
  const handleAssignToMe = async () => {
    if (!user?.id) return;
    
    const sellerName = `${user.first_name} ${user.last_name}`;
    await handleAssignToSeller(user.id, sellerName);
  };
  
  const handleAutoAssign = async () => {
    try {
      setAssigning('auto');
      setError(null);
      
      const response = await api.post(`/admin/core/sellers/conversations/${phone}/auto-assign`);
      
      if (response.data.success) {
        const seller = response.data.assignment;
        const sellerName = seller.seller_name || `${t('sellers.auto_assigned')}`;
        await onSellerSelected(seller.seller_id, sellerName);
      } else {
        setError(response.data.message || t('sellers.error_auto_assign'));
      }
    } catch (err: any) {
      console.error('Error auto assigning:', err);
      setError(err.response?.data?.detail || t('sellers.error_auto_assign'));
    } finally {
      setAssigning(null);
    }
  };
  
  const filteredSellers = sellers.filter(seller => {
    const fullName = `${seller.first_name} ${seller.last_name}`.toLowerCase();
    const matchesSearch = !searchQuery || 
      fullName.includes(searchQuery.toLowerCase()) ||
      seller.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      seller.role.toLowerCase().includes(searchQuery.toLowerCase());
    
    return matchesSearch;
  });
  
  const roleOptions = [
    { value: 'all', label: t('sellers.all_roles') },
    { value: 'setter', label: t('roles.setter') },
    { value: 'closer', label: t('roles.closer') },
    { value: 'professional', label: t('roles.professional') },
    { value: 'ceo', label: t('roles.ceo') }
  ];
  
  if (loading) {
    return (
      <div className={`p-4 text-center ${className}`}>
        <Loader2 className="animate-spin mx-auto text-gray-400" size={24} />
        <p className="text-gray-500 text-sm mt-2">{t('sellers.loading_sellers')}</p>
      </div>
    );
  }
  
  return (
    <div className={`bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users size={18} className="text-gray-600" />
            <h3 className="font-semibold text-gray-900">{t('sellers.assign_conversation')}</h3>
          </div>
          
          {onCancel && (
            <button
              onClick={onCancel}
              className="p-1 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
            >
              <X size={18} />
            </button>
          )}
        </div>
        
        <p className="text-sm text-gray-500 mt-1">
          {t('sellers.select_seller_for')}: <span className="font-mono text-gray-700">{phone}</span>
        </p>
      </div>
      
      {/* Current assignment */}
      {currentSellerId && (
        <div className="px-4 py-3 bg-blue-50 border-b border-blue-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm text-blue-700">{t('sellers.currently_assigned')}:</span>
              <SellerBadge
                sellerId={currentSellerId}
                sellerName={currentSellerName}
                sellerRole={currentSellerRole}
                size="sm"
              />
            </div>
          </div>
        </div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="px-4 py-3 bg-red-50 border-b border-red-100">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
      
      {/* Quick actions */}
      <div className="p-4 border-b border-gray-100 space-y-2">
        {showAssignToMe && user && (
          <button
            onClick={handleAssignToMe}
            disabled={assigning === user.id}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {assigning === user.id ? (
              <Loader2 className="animate-spin" size={18} />
            ) : (
              <UserPlus size={18} />
            )}
            {t('sellers.assign_to_me')}
          </button>
        )}
        
        {showAutoAssign && (
          <button
            onClick={handleAutoAssign}
            disabled={assigning === 'auto'}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {assigning === 'auto' ? (
              <Loader2 className="animate-spin" size={18} />
            ) : (
              <span>🤖</span>
            )}
            {t('sellers.auto_assign')}
          </button>
        )}
      </div>
      
      {/* Filters */}
      <div className="p-4 border-b border-gray-100 space-y-3">
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-gray-400" />
          <span className="text-xs font-medium text-gray-500">{t('sellers.filter_by_role')}</span>
        </div>
        
        <div className="flex flex-wrap gap-1.5">
          {roleOptions.map(option => (
            <button
              key={option.value}
              onClick={() => setRoleFilter(option.value)}
              className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
                roleFilter === option.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        
        <div>
          <input
            type="text"
            placeholder={t('sellers.search_placeholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>
      </div>
      
      {/* Sellers list */}
      <div className="max-h-64 overflow-y-auto">
        {filteredSellers.length === 0 ? (
          <div className="p-8 text-center">
            <User className="mx-auto text-gray-300" size={32} />
            <p className="text-gray-500 text-sm mt-2">{t('sellers.no_sellers_found')}</p>
            <button
              onClick={fetchSellers}
              className="mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              {t('sellers.retry')}
            </button>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filteredSellers.map(seller => {
              const isCurrent = seller.id === currentSellerId;
              const isAssigning = assigning === seller.id;
              const sellerName = `${seller.first_name} ${seller.last_name}`;
              
              return (
                <div
                  key={seller.id}
                  className={`p-3 hover:bg-gray-50 transition-colors ${
                    isCurrent ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
                          <User size={18} className="text-gray-600" />
                        </div>
                        {isCurrent && (
                          <div className="absolute -top-1 -right-1 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
                            <Check size={10} className="text-white" />
                          </div>
                        )}
                      </div>
                      
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">{sellerName}</span>
                          <span className={`px-1.5 py-0.5 text-xs rounded ${
                            seller.role === 'ceo' ? 'bg-purple-100 text-purple-700' :
                            seller.role === 'setter' ? 'bg-blue-100 text-blue-700' :
                            seller.role === 'closer' ? 'bg-green-100 text-green-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {t(`roles.${seller.role}`)}
                          </span>
                        </div>
                        
                        <p className="text-xs text-gray-500 mt-0.5">{seller.email}</p>
                        
                        {seller.active_conversations !== undefined && (
                          <div className="flex items-center gap-3 mt-1">
                            <span className="text-xs text-gray-500">
                              {t('sellers.active_conversations')}: {seller.active_conversations}
                            </span>
                            {seller.conversion_rate !== undefined && (
                              <span className="text-xs text-gray-500">
                                {t('sellers.conversion_rate')}: {seller.conversion_rate}%
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <button
                      onClick={() => handleAssignToSeller(seller.id, sellerName)}
                      disabled={isCurrent || isAssigning}
                      className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                        isCurrent
                          ? 'bg-blue-100 text-blue-700 cursor-default'
                          : 'bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed'
                      }`}
                    >
                      {isAssigning ? (
                        <Loader2 className="animate-spin" size={14} />
                      ) : isCurrent ? (
                        t('sellers.assigned')
                      ) : (
                        t('sellers.assign')
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
      
      {/* Footer */}
      <div className="p-3 bg-gray-50 border-t border-gray-100">
        <p className="text-xs text-gray-500 text-center">
          {t('sellers.total_sellers')}: {filteredSellers.length}
        </p>
      </div>
    </div>
  );
};

export default SellerSelector;
import React, { useState, useEffect } from 'react';
import { DataTable } from '../../components/DataTable';
import { Column } from '../../types/table';
import api from '../../api/client';
import { formatSiteTime } from '../../utils/timezone';
import { Plus, Edit2, Power, PowerOff } from 'lucide-react';

interface User {
  id: string;
  username: string;
  display_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  [key: string]: unknown;
}

export default function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [toastMsg, setToastMsg] = useState('');
  
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'add' | 'edit'>('add');
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  
  // Form state
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
    display_name: '',
    role: 'operator',
  });
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(''), 3000);
  };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await api.get('/users'); // Or /api/users depending on axios baseURL. baseURL is /api so '/users' -> /api/users
      if (response.data && response.data.users) {
        setUsers(response.data.users);
      }
    } catch (error) {
      showToast('获取用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleOpenAddModal = () => {
    setModalMode('add');
    setFormData({
      username: '',
      password: '',
      confirmPassword: '',
      display_name: '',
      role: 'operator',
    });
    setFormError('');
    setSelectedUser(null);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (user: User) => {
    setModalMode('edit');
    setFormData({
      username: user.username,
      password: '', // not edited here
      confirmPassword: '',
      display_name: user.display_name || '',
      role: user.role || 'operator',
    });
    setFormError('');
    setSelectedUser(user);
    setIsModalOpen(true);
  };

  const handleToggleStatus = async (user: User) => {
    if (user.username === 'boss') {
      showToast('不允许修改最高管理员状态');
      return;
    }
    try {
      // According to instructions: 停用/启用：调用 DELETE /api/users/{id}
      await api.delete(`/users/${user.id}`);
      showToast(`${user.is_active ? '停用' : '启用'}成功`);
      fetchUsers();
    } catch (error) {
      showToast('状态修改失败');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');

    if (modalMode === 'add') {
      if (!formData.username || !formData.password || !formData.confirmPassword) {
        setFormError('请填写所有必填项');
        return;
      }
      if (formData.password !== formData.confirmPassword) {
        setFormError('两次输入的密码不一致');
        return;
      }
    }

    setSubmitting(true);
    try {
      if (modalMode === 'add') {
        await api.post('/users', {
          username: formData.username,
          password: formData.password,
          display_name: formData.display_name,
          role: formData.role,
        });
        showToast('用户创建成功');
      } else {
        if (!selectedUser) return;
        await api.put(`/users/${selectedUser.id}`, {
          display_name: formData.display_name,
          role: formData.role,
        });
        showToast('用户信息更新成功');
      }
      setIsModalOpen(false);
      fetchUsers();
    } catch (error: unknown) {
      setFormError('操作失败，请重试');
    } finally {
      setSubmitting(false);
    }
  };

  const columns: Column<User>[] = [
    {
      key: 'index',
      title: '序号',
      width: 80,
      render: (_, __, index) => index + 1,
    },
    {
      key: 'username',
      title: '用户名',
      render: (val) => <span className="font-medium text-gray-900 dark:text-white">{String(val)}</span>,
    },
    {
      key: 'display_name',
      title: '显示名',
      render: (val) => String(val || '-'),
    },
    {
      key: 'role',
      title: '角色',
      render: (val) => {
        const isBoss = val === 'boss';
        return (
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${isBoss ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300' : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'}`}>
            {isBoss ? 'Boss' : 'Operator'}
          </span>
        );
      }
    },
    {
      key: 'is_active',
      title: '状态',
      render: (val) => {
        const isActive = Boolean(val);
        return (
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${isActive ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300'}`}>
            {isActive ? '活跃' : '停用'}
          </span>
        );
      }
    },
    {
      key: 'created_at',
      title: '创建时间',
      render: (val) => val ? formatSiteTime(new Date(String(val))) : '-',
    },
    {
      key: 'actions',
      title: '操作',
      render: (_, row) => {
        const isSelfBoss = row.username === 'boss';
        return (
          <div className="flex items-center space-x-3">
            <button
              onClick={() => handleOpenEditModal(row)}
              className="flex items-center text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
            >
              <Edit2 className="w-4 h-4 mr-1" />
              编辑
            </button>
            {!isSelfBoss && (
              <button
                onClick={() => handleToggleStatus(row)}
                className={`flex items-center text-sm ${row.is_active ? 'text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300' : 'text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-300'}`}
              >
                {row.is_active ? <PowerOff className="w-4 h-4 mr-1" /> : <Power className="w-4 h-4 mr-1" />}
                {row.is_active ? '停用' : '启用'}
              </button>
            )}
          </div>
        );
      }
    }
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            用户管理
            <span className="text-sm font-normal text-gray-500 dark:text-gray-400">
              (仅管理员可访问)
            </span>
          </h1>
        </div>
        <button
          onClick={handleOpenAddModal}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          <Plus className="w-4 h-4 mr-2" />
          新增用户
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <DataTable
          columns={columns}
          data={users}
          loading={loading}
          rowKey="id"
        />
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" onClick={() => !submitting && setIsModalOpen(false)}></div>
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <form onSubmit={handleSubmit}>
                <div className="px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                  <div className="flex justify-between items-center mb-5 border-b pb-4 dark:border-gray-700">
                    <h3 className="text-xl leading-6 font-medium text-gray-900 dark:text-white" id="modal-title">
                      {modalMode === 'add' ? '新增用户' : '编辑用户'}
                    </h3>
                    <button type="button" onClick={() => setIsModalOpen(false)} className="text-gray-400 hover:text-gray-500">
                      <span className="sr-only">Close</span>
                      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>

                  {formError && (
                    <div className="mb-4 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 p-3 rounded text-sm">
                      {formError}
                    </div>
                  )}

                  <div className="space-y-4">
                    {modalMode === 'add' && (
                      <>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">用户名 <span className="text-red-500">*</span></label>
                          <input
                            type="text"
                            required
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                            value={formData.username}
                            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                            placeholder="用于登录的账号"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">密码 <span className="text-red-500">*</span></label>
                          <input
                            type="password"
                            required
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                            value={formData.password}
                            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                            placeholder="输入密码"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">确认密码 <span className="text-red-500">*</span></label>
                          <input
                            type="password"
                            required
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                            value={formData.confirmPassword}
                            onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                            placeholder="再次输入密码"
                          />
                        </div>
                      </>
                    )}

                    {modalMode === 'edit' && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">用户名</label>
                        <input
                          type="text"
                          disabled
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 cursor-not-allowed"
                          value={formData.username}
                        />
                      </div>
                    )}

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">显示名</label>
                      <input
                        type="text"
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                        value={formData.display_name}
                        onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                        placeholder="例如：张三"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">角色</label>
                      <select
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                        value={formData.role}
                        onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                      >
                        <option value="operator">Operator (普通操作员)</option>
                        <option value="boss">Boss (管理员)</option>
                      </select>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 sm:px-6 flex justify-end space-x-3 border-t dark:border-gray-700">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    disabled={submitting}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none transition-colors"
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 transition-colors"
                  >
                    {submitting ? '提交中...' : '确定'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {toastMsg && (
        <div className="fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded shadow-lg z-50 transition-opacity">
          {toastMsg}
        </div>
      )}
    </div>
  );
}

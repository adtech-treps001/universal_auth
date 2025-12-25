/**
 * AdminPanel Organism Component
 * 
 * Comprehensive admin interface for managing authentication system.
 * Includes project configuration, role management, and system settings.
 */

import React, { useState } from 'react';
import { cn } from '../../utils/cn';
import Button from '../atoms/Button';
import Input from '../atoms/Input';
import Icon from '../atoms/Icon';

export interface AdminPanelProps {
  currentUser?: {
    id: string;
    name: string;
    email: string;
    role: string;
  };
  projects?: Array<{
    id: string;
    name: string;
    slug: string;
    status: 'active' | 'inactive';
    userCount: number;
  }>;
  roles?: Array<{
    id: string;
    name: string;
    capabilities: string[];
    userCount: number;
  }>;
  apiKeys?: Array<{
    id: string;
    name: string;
    provider: string;
    status: 'active' | 'inactive';
    lastUsed?: string;
  }>;
  onProjectCreate?: (project: any) => void;
  onProjectUpdate?: (id: string, updates: any) => void;
  onRoleCreate?: (role: any) => void;
  onRoleUpdate?: (id: string, updates: any) => void;
  onAPIKeyCreate?: (apiKey: any) => void;
  onAPIKeyUpdate?: (id: string, updates: any) => void;
  className?: string;
}

type TabType = 'overview' | 'projects' | 'roles' | 'apikeys' | 'settings';

const AdminPanel: React.FC<AdminPanelProps> = ({
  currentUser,
  projects = [],
  roles = [],
  apiKeys = [],
  onProjectCreate,
  onProjectUpdate,
  onRoleCreate,
  onRoleUpdate,
  onAPIKeyCreate,
  onAPIKeyUpdate,
  className
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createType, setCreateType] = useState<'project' | 'role' | 'apikey'>('project');

  const tabs = [
    { id: 'overview', label: 'Overview', icon: 'menu' },
    { id: 'projects', label: 'Projects', icon: 'settings' },
    { id: 'roles', label: 'Roles & Permissions', icon: 'user' },
    { id: 'apikeys', label: 'API Keys', icon: 'key' },
    { id: 'settings', label: 'Settings', icon: 'settings' }
  ];

  const renderOverview = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-blue-50 p-6 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-600">Total Projects</p>
              <p className="text-3xl font-bold text-blue-900">{projects.length}</p>
            </div>
            <Icon name="settings" className="text-blue-500" size="xl" />
          </div>
        </div>
        
        <div className="bg-green-50 p-6 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-600">Active Users</p>
              <p className="text-3xl font-bold text-green-900">
                {projects.reduce((sum, p) => sum + p.userCount, 0)}
              </p>
            </div>
            <Icon name="user" className="text-green-500" size="xl" />
          </div>
        </div>
        
        <div className="bg-purple-50 p-6 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-purple-600">API Keys</p>
              <p className="text-3xl font-bold text-purple-900">{apiKeys.length}</p>
            </div>
            <Icon name="key" className="text-purple-500" size="xl" />
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg border">
        <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
        <div className="space-y-3">
          {projects.slice(0, 5).map((project) => (
            <div key={project.id} className="flex items-center justify-between py-2 border-b last:border-b-0">
              <div className="flex items-center space-x-3">
                <div className={cn(
                  'w-2 h-2 rounded-full',
                  project.status === 'active' ? 'bg-green-500' : 'bg-gray-400'
                )} />
                <span className="font-medium">{project.name}</span>
                <span className="text-sm text-gray-500">{project.userCount} users</span>
              </div>
              <span className="text-sm text-gray-400">Active</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderProjects = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">Projects</h2>
        <Button
          onClick={() => {
            setCreateType('project');
            setShowCreateModal(true);
          }}
          leftIcon={<Icon name="plus" />}
        >
          Create Project
        </Button>
      </div>

      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Slug</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Users</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {projects.map((project) => (
              <tr key={project.id}>
                <td className="px-6 py-4 whitespace-nowrap font-medium">{project.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500">{project.slug}</td>
                <td className="px-6 py-4 whitespace-nowrap">{project.userCount}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={cn(
                    'px-2 py-1 text-xs font-medium rounded-full',
                    project.status === 'active' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-gray-100 text-gray-800'
                  )}>
                    {project.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex space-x-2">
                    <Button size="sm" variant="outline">
                      <Icon name="edit" size="sm" />
                    </Button>
                    <Button size="sm" variant="outline">
                      <Icon name="settings" size="sm" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderRoles = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">Roles & Permissions</h2>
        <Button
          onClick={() => {
            setCreateType('role');
            setShowCreateModal(true);
          }}
          leftIcon={<Icon name="plus" />}
        >
          Create Role
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {roles.map((role) => (
          <div key={role.id} className="bg-white p-6 rounded-lg border">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-lg">{role.name}</h3>
              <Button size="sm" variant="ghost">
                <Icon name="edit" size="sm" />
              </Button>
            </div>
            
            <div className="space-y-2 mb-4">
              <p className="text-sm text-gray-600">{role.userCount} users assigned</p>
              <p className="text-sm text-gray-600">{role.capabilities.length} capabilities</p>
            </div>
            
            <div className="space-y-1">
              <p className="text-xs font-medium text-gray-500 uppercase">Capabilities</p>
              <div className="flex flex-wrap gap-1">
                {role.capabilities.slice(0, 3).map((cap) => (
                  <span key={cap} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                    {cap}
                  </span>
                ))}
                {role.capabilities.length > 3 && (
                  <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                    +{role.capabilities.length - 3} more
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderAPIKeys = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">API Keys</h2>
        <Button
          onClick={() => {
            setCreateType('apikey');
            setShowCreateModal(true);
          }}
          leftIcon={<Icon name="plus" />}
        >
          Add API Key
        </Button>
      </div>

      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Provider</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Used</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {apiKeys.map((apiKey) => (
              <tr key={apiKey.id}>
                <td className="px-6 py-4 whitespace-nowrap font-medium">{apiKey.name}</td>
                <td className="px-6 py-4 whitespace-nowrap">{apiKey.provider}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={cn(
                    'px-2 py-1 text-xs font-medium rounded-full',
                    apiKey.status === 'active' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-gray-100 text-gray-800'
                  )}>
                    {apiKey.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                  {apiKey.lastUsed || 'Never'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex space-x-2">
                    <Button size="sm" variant="outline">
                      <Icon name="edit" size="sm" />
                    </Button>
                    <Button size="sm" variant="outline">
                      <Icon name="copy" size="sm" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderSettings = () => (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">System Settings</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg border">
          <h3 className="font-semibold mb-4">Authentication Settings</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span>Enable OAuth Providers</span>
              <input type="checkbox" defaultChecked className="rounded" />
            </div>
            <div className="flex items-center justify-between">
              <span>Require OTP Verification</span>
              <input type="checkbox" defaultChecked className="rounded" />
            </div>
            <div className="flex items-center justify-between">
              <span>Progressive Profiling</span>
              <input type="checkbox" defaultChecked className="rounded" />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border">
          <h3 className="font-semibold mb-4">Security Settings</h3>
          <div className="space-y-4">
            <Input
              label="Session Timeout (minutes)"
              type="number"
              defaultValue="30"
              fullWidth
            />
            <Input
              label="OTP Expiry (minutes)"
              type="number"
              defaultValue="5"
              fullWidth
            />
            <div className="flex items-center justify-between">
              <span>Enable Audit Logging</span>
              <input type="checkbox" defaultChecked className="rounded" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className={cn('min-h-screen bg-gray-50', className)}>
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Admin Panel</h1>
              <p className="text-gray-600">Universal Auth System</p>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                Welcome, {currentUser?.name || 'Admin'}
              </span>
              <Button variant="outline" size="sm">
                <Icon name="user" size="sm" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex space-x-8">
          {/* Sidebar */}
          <div className="w-64 flex-shrink-0">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as TabType)}
                  className={cn(
                    'w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                    activeTab === tab.id
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  )}
                >
                  <Icon name={tab.icon as any} size="sm" className="mr-3" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Main content */}
          <div className="flex-1">
            {activeTab === 'overview' && renderOverview()}
            {activeTab === 'projects' && renderProjects()}
            {activeTab === 'roles' && renderRoles()}
            {activeTab === 'apikeys' && renderAPIKeys()}
            {activeTab === 'settings' && renderSettings()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;
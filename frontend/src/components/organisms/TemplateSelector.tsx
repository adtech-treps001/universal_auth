/**
 * TemplateSelector Organism Component
 * 
 * Regional template selection interface for Indian-style mobile-first templates
 * and global templates. Provides region → category → template selection flow.
 */

"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Separator } from '../ui/separator';

interface Template {
  id: string;
  name: string;
  type: string;
  category: string;
  description: string;
  region: string;
  is_featured: boolean;
  config: any;
}

interface TemplateSelectorProps {
  onTemplateSelect: (template: Template) => void;
  selectedTemplate?: Template | null;
  className?: string;
}

export default function TemplateSelector({ 
  onTemplateSelect, 
  selectedTemplate, 
  className = "" 
}: TemplateSelectorProps) {
  const [selectedRegion, setSelectedRegion] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [availableRegions, setAvailableRegions] = useState<string[]>([]);
  const [availableCategories, setAvailableCategories] = useState<string[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'region' | 'category' | 'template'>('region');

  // Load available regions on component mount
  useEffect(() => {
    loadRegions();
  }, []);

  // Load categories when region is selected
  useEffect(() => {
    if (selectedRegion) {
      loadCategories(selectedRegion);
    }
  }, [selectedRegion]);

  // Load templates when category is selected
  useEffect(() => {
    if (selectedRegion && selectedCategory) {
      loadTemplates(selectedRegion, selectedCategory);
    }
  }, [selectedRegion, selectedCategory]);

  const loadRegions = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/projects/templates/regions');
      const data = await response.json();
      setAvailableRegions(data.regions || []);
    } catch (error) {
      console.error('Failed to load regions:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async (region: string) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/projects/templates/regions/${region}/categories`);
      const data = await response.json();
      setAvailableCategories(data.categories || []);
      setStep('category');
    } catch (error) {
      console.error('Failed to load categories:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTemplates = async (region: string, category: string) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/projects/templates/regions/${region}?category=${category}`);
      const data = await response.json();
      setTemplates(data.templates || []);
      setStep('template');
    } catch (error) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRegionSelect = (region: string) => {
    setSelectedRegion(region);
    setSelectedCategory('');
    setTemplates([]);
  };

  const handleCategorySelect = (category: string) => {
    setSelectedCategory(category);
  };

  const handleTemplateSelect = (template: Template) => {
    onTemplateSelect(template);
  };

  const handleBack = () => {
    if (step === 'template') {
      setStep('category');
      setTemplates([]);
    } else if (step === 'category') {
      setStep('region');
      setSelectedRegion('');
      setAvailableCategories([]);
    }
  };

  const getRegionDisplayName = (region: string) => {
    const regionNames: Record<string, string> = {
      'global': 'Global Templates',
      'india': 'Indian Templates (भारतीय टेम्प्लेट)'
    };
    return regionNames[region] || region;
  };

  const getCategoryDisplayName = (category: string) => {
    const categoryNames: Record<string, string> = {
      'fintech': 'Fintech (फिनटेक)',
      'ecommerce': 'E-commerce (ई-कॉमर्स)',
      'education': 'Education (शिक्षा)',
      'healthcare': 'Healthcare (स्वास्थ्य)',
      'enterprise': 'Enterprise',
      'startup': 'Startup',
      'community': 'Community'
    };
    return categoryNames[category] || category;
  };

  const renderRegionSelection = () => (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold mb-2">Select Region</h3>
        <p className="text-sm text-gray-600 mb-4">
          Choose your target region to see optimized templates
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {availableRegions.map((region) => (
          <Card 
            key={region}
            className={`cursor-pointer transition-all hover:shadow-md ${
              selectedRegion === region ? 'ring-2 ring-blue-500' : ''
            }`}
            onClick={() => handleRegionSelect(region)}
          >
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                {getRegionDisplayName(region)}
              </CardTitle>
              <CardDescription>
                {region === 'india' 
                  ? 'Mobile-first templates optimized for Indian users with progressive profiling'
                  : 'Universal templates suitable for global audiences'
                }
              </CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>
    </div>
  );

  const renderCategorySelection = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold mb-2">Select Category</h3>
          <p className="text-sm text-gray-600 mb-4">
            Choose the type of application you're building
          </p>
        </div>
        <Button variant="outline" onClick={handleBack}>
          ← Back to Regions
        </Button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {availableCategories.map((category) => (
          <Card 
            key={category}
            className={`cursor-pointer transition-all hover:shadow-md ${
              selectedCategory === category ? 'ring-2 ring-blue-500' : ''
            }`}
            onClick={() => handleCategorySelect(category)}
          >
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                {getCategoryDisplayName(category)}
              </CardTitle>
              <CardDescription>
                {category === 'fintech' && 'Banking, payments, and financial services'}
                {category === 'ecommerce' && 'Online shopping and marketplace platforms'}
                {category === 'education' && 'Learning platforms and educational tools'}
                {category === 'healthcare' && 'Medical and health-related applications'}
                {category === 'enterprise' && 'Business and corporate applications'}
                {category === 'startup' && 'Quick MVP and startup-focused setups'}
                {category === 'community' && 'Social platforms and community tools'}
              </CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>
    </div>
  );

  const renderTemplateSelection = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold mb-2">Select Template</h3>
          <p className="text-sm text-gray-600 mb-4">
            Choose a pre-configured template for your {getCategoryDisplayName(selectedCategory)} application
          </p>
        </div>
        <Button variant="outline" onClick={handleBack}>
          ← Back to Categories
        </Button>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {templates.map((template) => (
          <Card 
            key={template.id}
            className={`cursor-pointer transition-all hover:shadow-md ${
              selectedTemplate?.id === template.id ? 'ring-2 ring-blue-500' : ''
            } ${template.is_featured ? 'border-orange-200 bg-orange-50' : ''}`}
            onClick={() => handleTemplateSelect(template)}
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="text-base flex items-center gap-2">
                    {template.name}
                    {template.is_featured && (
                      <span className="text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded-full">
                        Featured
                      </span>
                    )}
                  </CardTitle>
                  <CardDescription className="mt-2">
                    {template.description}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            
            <CardContent className="pt-0">
              <div className="space-y-3">
                {/* Template features preview */}
                {template.config && (
                  <div className="space-y-2">
                    {template.config.auth && (
                      <div className="text-sm">
                        <span className="font-medium">Auth:</span>{' '}
                        {template.config.auth.primary_method === 'mobile_otp' 
                          ? 'Mobile OTP (मोबाइल OTP)' 
                          : 'Email/Social Login'
                        }
                      </div>
                    )}
                    
                    {template.config.ui && (
                      <div className="text-sm">
                        <span className="font-medium">UI:</span>{' '}
                        {template.config.ui.mobile_first ? 'Mobile-First' : 'Responsive'}{' '}
                        {template.config.ui.language_options && 
                          `(${template.config.ui.language_options.join(', ')})`
                        }
                      </div>
                    )}
                    
                    {template.config.workflow && template.config.workflow.progressive_profiling && (
                      <div className="text-sm">
                        <span className="font-medium">Features:</span> Progressive Profiling
                        {template.config.workflow.kyc_integration && ', KYC Integration'}
                      </div>
                    )}
                  </div>
                )}
                
                <Separator />
                
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-500">
                    Region: {template.region === 'india' ? 'India (भारत)' : 'Global'}
                  </span>
                  <Button 
                    size="sm" 
                    variant={selectedTemplate?.id === template.id ? "default" : "outline"}
                  >
                    {selectedTemplate?.id === template.id ? 'Selected' : 'Select'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      
      {templates.length === 0 && !loading && (
        <div className="text-center py-8 text-gray-500">
          No templates available for this category
        </div>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className={`flex items-center justify-center py-8 ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-sm text-gray-600">Loading templates...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {step === 'region' && renderRegionSelection()}
      {step === 'category' && renderCategorySelection()}
      {step === 'template' && renderTemplateSelection()}
    </div>
  );
}
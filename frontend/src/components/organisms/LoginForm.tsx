"use client";

import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Github, Mail, Linkedin, Phone, Shield } from "lucide-react";

export interface LoginFormProps {
  onOAuthLogin?: (provider: string) => void;
  onOTPRequest?: (mobile: string) => void;
  onOTPVerify?: (otp: string) => void;
  loading?: boolean;
  error?: string;
  step?: 'provider' | 'mobile' | 'otp';
  className?: string;
}

const LoginForm: React.FC<LoginFormProps> = ({
  onOAuthLogin,
  onOTPRequest,
  onOTPVerify,
  loading = false,
  error,
  step = 'provider',
  className
}) => {
  const [mobile, setMobile] = useState('');
  const [otp, setOTP] = useState('');
  const [mobileError, setMobileError] = useState('');

  const validateMobile = (mobile: string): boolean => {
    // Indian mobile number validation
    const indianMobileRegex = /^[6-9]\d{9}$/;
    if (!indianMobileRegex.test(mobile)) {
      setMobileError('Please enter a valid Indian mobile number');
      return false;
    }
    setMobileError('');
    return true;
  };

  const handleMobileSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validateMobile(mobile)) {
      onOTPRequest?.(mobile);
    }
  };

  const handleOTPSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length === 6) {
      onOTPVerify?.(otp);
    }
  };

  const renderProviderStep = () => (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center w-12 h-12 mx-auto bg-primary/10 rounded-full">
          <Shield className="w-6 h-6 text-primary" />
        </div>
        <CardTitle className="text-2xl font-bold">Welcome Back</CardTitle>
        <CardDescription>
          Choose your preferred sign-in method to continue
        </CardDescription>
      </div>

      <div className="space-y-3">
        <Button
          variant="outline"
          size="lg"
          className="w-full h-12 text-left justify-start gap-3 hover:bg-red-50 hover:border-red-200 transition-colors"
          onClick={() => onOAuthLogin?.('google')}
          disabled={loading}
        >
          <Mail className="w-5 h-5 text-red-500" />
          <span className="flex-1">Continue with Google</span>
        </Button>
        
        <Button
          variant="outline"
          size="lg"
          className="w-full h-12 text-left justify-start gap-3 hover:bg-gray-50 hover:border-gray-300 transition-colors"
          onClick={() => onOAuthLogin?.('github')}
          disabled={loading}
        >
          <Github className="w-5 h-5 text-gray-700" />
          <span className="flex-1">Continue with GitHub</span>
        </Button>
        
        <Button
          variant="outline"
          size="lg"
          className="w-full h-12 text-left justify-start gap-3 hover:bg-blue-50 hover:border-blue-200 transition-colors"
          onClick={() => onOAuthLogin?.('linkedin')}
          disabled={loading}
        >
          <Linkedin className="w-5 h-5 text-blue-600" />
          <span className="flex-1">Continue with LinkedIn</span>
        </Button>
      </div>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <Separator className="w-full" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">
            Or continue with mobile
          </span>
        </div>
      </div>

      <form onSubmit={handleMobileSubmit} className="space-y-4">
        <div className="space-y-2">
          <div className="relative">
            <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="tel"
              placeholder="Enter mobile number"
              value={mobile}
              onChange={(e) => setMobile(e.target.value)}
              className="pl-10 h-12"
              disabled={loading}
            />
          </div>
          {mobileError && (
            <p className="text-sm text-destructive">{mobileError}</p>
          )}
        </div>
        <Button
          type="submit"
          size="lg"
          className="w-full h-12"
          disabled={!mobile || loading}
        >
          {loading ? "Sending..." : "Send OTP"}
        </Button>
      </form>
    </div>
  );

  const renderOTPStep = () => (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center w-12 h-12 mx-auto bg-primary/10 rounded-full">
          <Phone className="w-6 h-6 text-primary" />
        </div>
        <CardTitle className="text-2xl font-bold">Verify OTP</CardTitle>
        <CardDescription>
          Enter the 6-digit code sent to +91 {mobile}
        </CardDescription>
      </div>

      <form onSubmit={handleOTPSubmit} className="space-y-4">
        <div className="space-y-2">
          <Input
            type="text"
            placeholder="Enter 6-digit OTP"
            value={otp}
            onChange={(e) => setOTP(e.target.value.replace(/\D/g, '').slice(0, 6))}
            className="text-center text-lg tracking-widest h-12"
            maxLength={6}
            disabled={loading}
          />
        </div>
        <Button
          type="submit"
          size="lg"
          className="w-full h-12"
          disabled={otp.length !== 6 || loading}
        >
          {loading ? "Verifying..." : "Verify OTP"}
        </Button>
      </form>

      <div className="text-center">
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground hover:text-foreground"
          disabled={loading}
        >
          Resend OTP
        </Button>
      </div>
    </div>
  );

  return (
    <Card className="w-full max-w-md mx-auto shadow-lg">
      <CardHeader className="pb-4">
        {error && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
            <p className="text-sm text-destructive text-center">{error}</p>
          </div>
        )}
      </CardHeader>
      <CardContent className="pb-6">
        {step === 'provider' && renderProviderStep()}
        {step === 'otp' && renderOTPStep()}
      </CardContent>
    </Card>
  );
};

export default LoginForm;
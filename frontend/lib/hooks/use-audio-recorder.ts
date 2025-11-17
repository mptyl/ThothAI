// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

import { useState, useRef, useCallback } from 'react';

interface UseAudioRecorderOptions {
  onRecordingComplete?: (audioBlob: Blob) => void;
  onRecordingStart?: () => void;
  onRecordingStop?: () => void;
  onError?: (error: string) => void;
}

export const useAudioRecorder = (options: UseAudioRecorderOptions = {}) => {
  const {
    onRecordingComplete,
    onRecordingStart,
    onRecordingStop,
    onError
  } = options;

  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isSupported, setIsSupported] = useState(
    typeof window !== 'undefined' && 
    !!navigator.mediaDevices && 
    !!navigator.mediaDevices.getUserMedia &&
    typeof MediaRecorder !== 'undefined'
  );

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const startRecording = useCallback(async () => {
    if (!isSupported) {
      onError?.('Audio recording is not supported in this browser');
      return;
    }

    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000, // Optimal for Whisper
        }
      });

      streamRef.current = stream;
      chunksRef.current = [];

      // Create MediaRecorder with optimal settings for Whisper
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus', // Fallback to audio/webm if needed
      });

      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(chunksRef.current, { 
          type: 'audio/webm;codecs=opus' 
        });
        
        onRecordingComplete?.(audioBlob);
        onRecordingStop?.();
        
        // Cleanup
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
      };

      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event);
        onError?.('Recording failed');
        stopRecording();
      };

      // Start recording
      mediaRecorder.start(1000); // Collect data every second
      setIsRecording(true);
      setRecordingTime(0);
      onRecordingStart?.();

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

    } catch (error) {
      console.error('Error starting recording:', error);
      onError?.('Failed to access microphone. Please check permissions.');
    }
  }, [isSupported, onRecordingComplete, onRecordingStart, onRecordingStop, onError]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  }, [isRecording]);

  const cancelRecording = useCallback(() => {
    if (isRecording) {
      setIsRecording(false);
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }

      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }

      if (mediaRecorderRef.current) {
        mediaRecorderRef.current = null;
      }

      chunksRef.current = [];
      setRecordingTime(0);
    }
  }, [isRecording]);

  // Cleanup on unmount
  const cleanup = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
  }, []);

  return {
    isRecording,
    recordingTime,
    isSupported,
    startRecording,
    stopRecording,
    cancelRecording,
    cleanup
  };
};
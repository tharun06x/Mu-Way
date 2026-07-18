import axios from 'axios';
import type { RoadmapApiResponse, CompareRolesApiResponse, InsightsApiResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : '');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  generateRoadmap: async (
    muid: string,
    name: string,
    role: string,
    regenerate = false,
  ): Promise<RoadmapApiResponse> => {
    const response = await apiClient.post<RoadmapApiResponse>('/generate_roadmap', {
      muid,
      name,
      role,
      enable_decay: true,
      enrich_tasks: true,
      regenerate,
    });
    return response.data;
  },

  compareRoles: async (muid: string, roleA: string, roleB: string): Promise<CompareRolesApiResponse> => {
    const response = await apiClient.post<CompareRolesApiResponse>('/compare_roles', {
      muid,
      role_a: roleA,
      role_b: roleB,
    });
    return response.data;
  },

  getInsights: async (muid: string): Promise<InsightsApiResponse> => {
    const response = await apiClient.post<InsightsApiResponse>('/insights', { muid });
    return response.data;
  },
};

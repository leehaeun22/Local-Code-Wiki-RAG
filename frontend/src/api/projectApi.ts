import { apiClient } from './client'
import type { FileTreeNode, RepositoryScanResult } from '../types/file'
import type {
  ApiResponse,
  Project,
  ProjectCreateRequest,
  ProjectUpdateRequest,
} from '../types/project'

export const projectApi = {
  async createProject(payload: ProjectCreateRequest) {
    const { data } = await apiClient.post<ApiResponse<Project>>('/api/v1/projects', payload)
    return data.data
  },

  async getProjects() {
    const { data } = await apiClient.get<ApiResponse<Project[]>>('/api/v1/projects')
    return data.data
  },

  async getProject(projectId: string) {
    const { data } = await apiClient.get<ApiResponse<Project>>(`/api/v1/projects/${projectId}`)
    return data.data
  },

  async updateProject(projectId: string, payload: ProjectUpdateRequest) {
    const { data } = await apiClient.patch<ApiResponse<Project>>(
      `/api/v1/projects/${projectId}`,
      payload,
    )
    return data.data
  },

  async deleteProject(projectId: string) {
    const { data } = await apiClient.delete<ApiResponse<{ id: string }>>(
      `/api/v1/projects/${projectId}`,
    )
    return data.data
  },

  async scanProject(projectId: string) {
    const { data } = await apiClient.post<ApiResponse<RepositoryScanResult>>(
      `/api/v1/projects/${projectId}/scan`,
    )
    return data.data
  },

  async getFileTree(projectId: string) {
    const { data } = await apiClient.get<ApiResponse<FileTreeNode[]>>(
      `/api/v1/projects/${projectId}/file-tree`,
    )
    return data.data
  },
}

import { apiClient } from './client'
import type { ChatSession, ChatSessionCreateRequest, RagChatRequest, RagChatResponse } from '../types/chat'
import type {
  DocumentGenerateRequest,
  DocumentGenerationResult,
  ProjectDocument,
} from '../types/document'
import type {
  CodeChunk,
  CodeChunkGenerationResult,
  FileTreeNode,
  RepositoryScanResult,
} from '../types/file'
import type {
  ApiResponse,
  AnalysisStatus,
  Project,
  ProjectCloneResult,
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

  async getAnalysisStatus(projectId: string) {
    const { data } = await apiClient.get<ApiResponse<AnalysisStatus>>(
      `/api/v1/projects/${projectId}/analysis-status`,
    )
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

  async cloneProject(projectId: string) {
    const { data } = await apiClient.post<ApiResponse<ProjectCloneResult>>(
      `/api/v1/projects/${projectId}/clone`,
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

  async generateCodeChunks(projectId: string) {
    const { data } = await apiClient.post<ApiResponse<CodeChunkGenerationResult>>(
      `/api/v1/projects/${projectId}/chunks/generate`,
    )
    return data.data
  },

  async getCodeChunks(projectId: string) {
    const { data } = await apiClient.get<ApiResponse<CodeChunk[]>>(
      `/api/v1/projects/${projectId}/chunks`,
    )
    return data.data
  },

  async createChatSession(projectId: string, payload: ChatSessionCreateRequest) {
    const { data } = await apiClient.post<ApiResponse<ChatSession>>(
      `/api/v1/projects/${projectId}/chat/sessions`,
      payload,
    )
    return data.data
  },

  async sendChatMessage(projectId: string, payload: RagChatRequest) {
    const { data } = await apiClient.post<ApiResponse<RagChatResponse>>(
      `/api/v1/projects/${projectId}/chat`,
      payload,
    )
    return data.data
  },

  async generateDocuments(projectId: string, payload: DocumentGenerateRequest) {
    const { data } = await apiClient.post<ApiResponse<DocumentGenerationResult>>(
      `/api/v1/projects/${projectId}/documents/generate`,
      payload,
    )
    return data.data
  },

  async getDocuments(projectId: string) {
    const { data } = await apiClient.get<ApiResponse<ProjectDocument[]>>(
      `/api/v1/projects/${projectId}/documents`,
    )
    return data.data
  },

  async getDocument(projectId: string, documentId: string) {
    const { data } = await apiClient.get<ApiResponse<ProjectDocument>>(
      `/api/v1/projects/${projectId}/documents/${documentId}`,
    )
    return data.data
  },
}

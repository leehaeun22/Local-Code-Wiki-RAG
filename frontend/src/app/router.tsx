import { Route, Routes } from 'react-router-dom'

import { ProjectCreatePage } from '../pages/ProjectCreatePage'
import { ProjectDetailPage } from '../pages/ProjectDetailPage'
import { ProjectListPage } from '../pages/ProjectListPage'

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<ProjectListPage />} />
      <Route path="/projects/new" element={<ProjectCreatePage />} />
      <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
    </Routes>
  )
}

export async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(
      typeof body.detail === 'string' ? body.detail : `Request failed (${response.status}).`,
    )
  }
  return response.json()
}

export async function downloadDataset(id: string, format: string) {
  const response = await fetch(`/api/datasets/${encodeURIComponent(id)}/download/${format}`)
  if (!response.ok) throw new Error('Download failed. Refresh the dataset and try again.')
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = `${id}.${format === 'metadata' ? 'metadata.json' : format}`
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

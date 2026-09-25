async function request(url: string, signal?: AbortSignal): Promise<Response> {
  const timeout = AbortSignal.timeout(30_000)
  try {
    return await fetch(url, { signal: signal ? AbortSignal.any([signal, timeout]) : timeout })
  } catch (error) {
    if (signal?.aborted) throw error
    if (timeout.aborted)
      throw new Error('The data service took too long. Try again with a smaller dataset.', {
        cause: error,
      })
    throw new Error(
      'Cannot reach the data service. Start the backend on port 8000 and try again.',
      { cause: error },
    )
  }
}

async function checkResponse(response: Response) {
  if (response.ok) return
  const body = await response.json().catch(() => ({}))
  throw new Error(
    typeof body?.detail === 'string'
      ? body.detail
      : `Data service error (${response.status}). Check the backend terminal and try again.`,
  )
}

export async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await request(url, signal)
  await checkResponse(response)
  try {
    return await response.json()
  } catch {
    throw new Error(
      'The data service returned an invalid response. Restart the frontend and backend, then try again.',
    )
  }
}

export async function downloadDataset(id: string, format: string) {
  const response = await request(`/api/datasets/${encodeURIComponent(id)}/download/${format}`)
  await checkResponse(response)
  const contentType = response.headers.get('content-type') ?? ''
  const expected =
    format === 'gpkg'
      ? ['application/geopackage+sqlite3']
      : ['application/json', 'application/geo+json']
  if (!expected.some((type) => contentType.split(';')[0].trim() === type)) {
    throw new Error(
      'Download returned an unexpected file type. Restart the services and try again.',
    )
  }
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = `${id}.${format === 'metadata' ? 'metadata.json' : format}`
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

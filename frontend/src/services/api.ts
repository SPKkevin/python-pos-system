import axios from "axios";

const api = axios.create({
    baseURL:"http://127.0.0.1:8000",
    timeout: 5000,
})

export default api

export async function safeRequest<T>(fn: () => Promise<T>): Promise<T | null> {
  try {
    return await fn()
  } catch (err) {
    console.error(err)
    return null
  }
}
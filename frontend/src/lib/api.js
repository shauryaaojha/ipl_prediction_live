/**
 * API fetcher for the Next.js frontend to communicate with the FastAPI backend.
 * Uses native fetch with caching and revalidation support.
 */

const isServer = typeof window === 'undefined';
const API_BASE_URL = isServer 
  ? process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Generic GET fetcher
 * @param {string} endpoint - The API endpoint (e.g., "/matches")
 * @param {object} options - Fetch options (next cache/revalidate)
 * @returns {Promise<any>}
 */
export async function fetchApi(endpoint, options = {}) {
  // Default to caching for 60 seconds unless specified
  const defaultOptions = {
    next: { revalidate: 60 },
    ...options,
  };

  try {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, defaultOptions);

    if (!res.ok) {
      console.error(`API Error ${res.status} on ${endpoint}:`, await res.text());
      return null;
    }

    return await res.json();
  } catch (error) {
    console.error(`Failed to fetch ${endpoint}:`, error);
    return null;
  }
}

// ----------------------------------------------------------------------
// Specific API Helpers
// ----------------------------------------------------------------------

export async function getDashboardStats() {
  // A quick way to get total matches, players, etc.
  // Since we don't have a single /stats endpoint, we can aggregate
  const [matchesRes, playersRes, venuesRes] = await Promise.all([
    fetchApi('/matches?per_page=1'),
    fetchApi('/players?per_page=1'),
    fetchApi('/venues'),
  ]);

  return {
    totalMatches: matchesRes?.pagination?.total || 0,
    totalPlayers: playersRes?.pagination?.total || 0,
    totalVenues: venuesRes?.length || 0,
  };
}

export async function search(query) {
  if (!query) return null;
  return fetchApi(`/search?q=${encodeURIComponent(query)}`);
}

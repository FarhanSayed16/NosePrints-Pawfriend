import { useState, useEffect } from "react";
import { getDogs } from "../services/api";
import "./Directory.css";

export default function Directory() {
  const [dogs, setDogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    breed: "",
    color: "",
    status: "",
    name: "",
  });
  const [page, setPage] = useState(1);

  const fetchDogs = async () => {
    setLoading(true);
    try {
      const params = { page, per_page: 20 };
      if (filters.breed) params.breed = filters.breed;
      if (filters.color) params.color = filters.color;
      if (filters.status) params.status = filters.status;
      if (filters.name) params.name = filters.name;

      const res = await getDogs(params);
      setDogs(res.data);
    } catch (err) {
      console.error("Failed to fetch dogs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDogs();
  }, [page]);

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    fetchDogs();
  };

  const clearFilters = () => {
    setFilters({ breed: "", color: "", status: "", name: "" });
    setPage(1);
    setTimeout(fetchDogs, 0);
  };

  return (
    <div className="page directory-page">
      <div className="container">
        <div className="page-header">
          <h1>
            Dog <span className="text-gradient">Directory</span>
          </h1>
          <p>Browse all registered dogs — search by breed, color, or name</p>
        </div>

        {/* Search/Filter Bar */}
        <form onSubmit={handleSearch} className="filter-bar glass-card">
          <div className="filter-inputs">
            <input
              className="form-input"
              type="text"
              placeholder="🔍 Search by name..."
              value={filters.name}
              onChange={(e) => setFilters({ ...filters, name: e.target.value })}
            />
            <input
              className="form-input"
              type="text"
              placeholder="🏷️ Breed..."
              value={filters.breed}
              onChange={(e) => setFilters({ ...filters, breed: e.target.value })}
            />
            <input
              className="form-input"
              type="text"
              placeholder="🎨 Color..."
              value={filters.color}
              onChange={(e) => setFilters({ ...filters, color: e.target.value })}
            />
            <select
              className="form-select"
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            >
              <option value="">All Status</option>
              <option value="registered">✅ Registered</option>
              <option value="lost">🚨 Lost</option>
              <option value="found">🔎 Found</option>
            </select>
          </div>
          <div className="filter-actions">
            <button className="btn btn-primary btn-sm" type="submit">
              Search
            </button>
            <button className="btn btn-outline btn-sm" type="button" onClick={clearFilters}>
              Clear
            </button>
          </div>
        </form>

        {/* Loading */}
        {loading && (
          <div className="text-center mt-4">
            <div className="progress-spinner"></div>
            <p className="mt-1" style={{ color: "var(--clr-text-muted)" }}>
              Loading dogs...
            </p>
          </div>
        )}

        {/* Results */}
        {!loading && dogs.length === 0 && (
          <div className="glass-card text-center mt-3" style={{ padding: "3rem" }}>
            <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🐕</div>
            <h3>No dogs found</h3>
            <p style={{ color: "var(--clr-text-muted)" }}>
              Try adjusting your search filters, or register the first dog!
            </p>
          </div>
        )}

        {!loading && dogs.length > 0 && (
          <>
            <div className="dogs-grid stagger-children">
              {dogs.map((dog) => (
                <div key={dog.id} className="dog-card glass-card">
                  <div className="dog-card-header">
                    <div className="dog-avatar">
                      {dog.profile_photo_url ? (
                        <img src={dog.profile_photo_url} alt={dog.name} />
                      ) : (
                        <span className="avatar-placeholder">🐕</span>
                      )}
                    </div>
                    <span className={`badge badge-${dog.status}`}>
                      {dog.status}
                    </span>
                  </div>
                  <h3 className="dog-name">{dog.name || "Unnamed"}</h3>
                  <div className="dog-meta">
                    {dog.breed && (
                      <span className="meta-item">🏷️ {dog.breed}</span>
                    )}
                    {dog.color && (
                      <span className="meta-item">🎨 {dog.color}</span>
                    )}
                    {dog.sex && (
                      <span className="meta-item">
                        {dog.sex === "male" ? "♂️" : "♀️"} {dog.sex}
                      </span>
                    )}
                  </div>
                  <div className="dog-footer">
                    <span className="noseprint-count">
                      🐾 {dog.nose_print_count || 0} nose prints
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            <div className="pagination">
              <button
                className="btn btn-outline btn-sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                ← Previous
              </button>
              <span className="page-number">Page {page}</span>
              <button
                className="btn btn-outline btn-sm"
                disabled={dogs.length < 20}
                onClick={() => setPage(page + 1)}
              >
                Next →
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

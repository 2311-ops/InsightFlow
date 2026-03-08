namespace InsightFlow.Backend.Models;

// ── User ──────────────────────────────────────────────────────────
public class User
{
    public int UserId { get; set; }
    public string Email { get; set; } = string.Empty;
    public string PasswordHash { get; set; } = string.Empty;
    public string FirstName { get; set; } = string.Empty;
    public string LastName { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // Navigation
    public ICollection<Company> Companies { get; set; } = new List<Company>();
}

// ── Company ───────────────────────────────────────────────────────
public class Company
{
    public int CompanyId { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Industry { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // FK
    public int UserId { get; set; }
    public User User { get; set; } = null!;

    // Navigation
    public ICollection<Dataset> Datasets { get; set; } = new List<Dataset>();
}

// ── Dataset ───────────────────────────────────────────────────────
public class Dataset
{
    public int DatasetId { get; set; }
    public string FileName { get; set; } = string.Empty;
    public string FilePath { get; set; } = string.Empty;   // stored on disk
    public long FileSizeBytes { get; set; }
    public string Status { get; set; } = "uploaded";       // uploaded | processing | done | error
    public DateTime UploadedAt { get; set; } = DateTime.UtcNow;

    // FK
    public int CompanyId { get; set; }
    public Company Company { get; set; } = null!;

    // Navigation
    public ICollection<Metric> Metrics { get; set; } = new List<Metric>();
    public ICollection<Insight> Insights { get; set; } = new List<Insight>();
}

// ── Metric ────────────────────────────────────────────────────────
public class Metric
{
    public int MetricId { get; set; }
    public string Name { get; set; } = string.Empty;       // e.g. "total_revenue"
    public double Value { get; set; }
    public string Unit { get; set; } = string.Empty;       // e.g. "USD", "%", "count"
    public DateTime ComputedAt { get; set; } = DateTime.UtcNow;

    // FK
    public int DatasetId { get; set; }
    public Dataset Dataset { get; set; } = null!;
}

// ── Insight ───────────────────────────────────────────────────────
public class Insight
{
    public int InsightId { get; set; }
    public string Content { get; set; } = string.Empty;    // AI-generated text
    public string Type { get; set; } = "general";          // general | anomaly | recommendation
    public DateTime GeneratedAt { get; set; } = DateTime.UtcNow;

    // FK
    public int DatasetId { get; set; }
    public Dataset Dataset { get; set; } = null!;
}

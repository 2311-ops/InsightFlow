using Microsoft.EntityFrameworkCore;
using InsightFlow.Backend.Models;

namespace InsightFlow.Backend.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<User> Users => Set<User>();
    public DbSet<Company> Companies => Set<Company>();
    public DbSet<Dataset> Datasets => Set<Dataset>();
    public DbSet<Metric> Metrics => Set<Metric>();
    public DbSet<Insight> Insights => Set<Insight>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // User
        modelBuilder.Entity<User>(e =>
        {
            e.HasKey(u => u.UserId);
            e.HasIndex(u => u.Email).IsUnique();
            e.Property(u => u.Email).IsRequired().HasMaxLength(255);
            e.Property(u => u.PasswordHash).IsRequired();
        });

        // Company → User (many-to-one)
        modelBuilder.Entity<Company>(e =>
        {
            e.HasKey(c => c.CompanyId);
            e.Property(c => c.Name).IsRequired().HasMaxLength(200);
            e.HasOne(c => c.User)
             .WithMany(u => u.Companies)
             .HasForeignKey(c => c.UserId)
             .OnDelete(DeleteBehavior.Cascade);
        });

        // Dataset → Company
        modelBuilder.Entity<Dataset>(e =>
        {
            e.HasKey(d => d.DatasetId);
            e.Property(d => d.FileName).IsRequired().HasMaxLength(500);
            e.HasOne(d => d.Company)
             .WithMany(c => c.Datasets)
             .HasForeignKey(d => d.CompanyId)
             .OnDelete(DeleteBehavior.Cascade);
        });

        // Metric → Dataset
        modelBuilder.Entity<Metric>(e =>
        {
            e.HasKey(m => m.MetricId);
            e.HasOne(m => m.Dataset)
             .WithMany(d => d.Metrics)
             .HasForeignKey(m => m.DatasetId)
             .OnDelete(DeleteBehavior.Cascade);
        });

        // Insight → Dataset
        modelBuilder.Entity<Insight>(e =>
        {
            e.HasKey(i => i.InsightId);
            e.HasOne(i => i.Dataset)
             .WithMany(d => d.Insights)
             .HasForeignKey(i => i.DatasetId)
             .OnDelete(DeleteBehavior.Cascade);
        });
    }
}

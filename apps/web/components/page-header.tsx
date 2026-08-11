interface PageHeaderProps {
  title: string;
  description?: string;
  children?: React.ReactNode;
}

export function PageHeader({ title, description, children }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between p-4 rounded-2xl glass-card border border-white/20 dark:border-white/10">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-foreground bg-clip-text bg-gradient-to-r from-foreground via-foreground/90 to-primary/80">
          {title}
        </h1>
        {description ? <p className="mt-1 text-xs text-muted-foreground">{description}</p> : null}
      </div>
      {children ? <div className="flex flex-wrap items-center gap-2">{children}</div> : null}
    </div>
  );
}

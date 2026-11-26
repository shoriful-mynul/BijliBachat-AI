type PageHeaderProps = {
  title: string;
  description?: string;
};

export function PageHeader({ title, description }: PageHeaderProps) {
  return (
    <div className="min-w-0">
      <h1 className="truncate font-display text-lg font-semibold leading-snug md:text-xl">
        {title}
      </h1>
      {description ? (
        <p className="mt-0.5 hidden text-sm leading-5 text-muted sm:line-clamp-2 sm:block">
          {description}
        </p>
      ) : null}
    </div>
  );
}

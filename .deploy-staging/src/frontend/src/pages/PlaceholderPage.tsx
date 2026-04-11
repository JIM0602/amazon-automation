interface PlaceholderPageProps {
  title?: string;
}

export default function PlaceholderPage({ title = '页面建设中' }: PlaceholderPageProps) {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <div className="text-4xl mb-4">🚧</div>
        <h1 className="text-xl font-medium text-white mb-2">{title}</h1>
        <p className="text-gray-400 text-sm">该页面正在建设中，敬请期待</p>
      </div>
    </div>
  );
}

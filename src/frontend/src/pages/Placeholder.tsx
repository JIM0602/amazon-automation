import { useLocation } from 'react-router-dom';

export default function Placeholder() {
  const location = useLocation();

  return (
    <div className="p-6 h-full flex items-center justify-center text-white">
      <div className="glass p-8 rounded-xl flex flex-col items-center">
        <h1 className="text-2xl font-bold mb-4">Placeholder Page</h1>
        <p className="text-gray-300">Current Route: {location.pathname}</p>
      </div>
    </div>
  );
}

const base =
  'bg-white rounded-xl shadow-sm border border-gray-100';

export const Card = ({ className = '', children }) => (
  <div className={`${base} ${className}`}>{children}</div>
);

export const CardHeader = ({ className = '', children }) => (
  <div className={`px-6 py-4 border-b border-gray-100 ${className}`}>{children}</div>
);

export const CardTitle = ({ className = '', children }) => (
  <h2 className={`text-lg font-semibold text-gray-900 ${className}`}>{children}</h2>
);

export const CardContent = ({ className = '', children }) => (
  <div className={`px-6 py-4 ${className}`}>{children}</div>
);


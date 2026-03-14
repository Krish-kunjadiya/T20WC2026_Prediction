const base =
  'inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition disabled:opacity-60 disabled:cursor-not-allowed';

const variants = {
  primary: 'bg-primary-600 text-white hover:bg-primary-700',
  ghost: 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50',
};

const Button = ({ variant = 'primary', className = '', ...props }) => {
  return <button className={`${base} ${variants[variant]} ${className}`} {...props} />;
};

export default Button;


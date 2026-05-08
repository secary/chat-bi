type SwitchProps = {
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
  'aria-label'?: string;
  id?: string;
};

export function Switch({
  checked,
  onChange,
  disabled = false,
  'aria-label': ariaLabel,
  id,
}: SwitchProps) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      aria-label={ariaLabel}
      onClick={() => !disabled && onChange(!checked)}
      className={
        'relative h-4 w-8 shrink-0 rounded-full border border-transparent transition-colors ' +
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 ' +
        'focus-visible:outline-gray-400 disabled:cursor-not-allowed disabled:opacity-50 ' +
        (checked ? 'bg-emerald-500' : 'bg-gray-200')
      }
    >
      <span
        className={
          'pointer-events-none absolute inset-y-[1px] left-[1px] h-3 w-3 rounded-full bg-white shadow-sm ' +
          'transition-transform duration-200 ease-out ' +
          (checked ? 'translate-x-4' : 'translate-x-0')
        }
        aria-hidden
      />
    </button>
  );
}

"use client";
import { useState } from "react";

export default function StarRating({ value = 0, onChange, size = "md", readonly = false }) {
  const [hover, setHover] = useState(0);
  const stars = [1, 2, 3, 4, 5];

  const sizeClass = size === "lg" ? "text-3xl" : size === "sm" ? "text-lg" : "text-2xl";

  return (
    <div className="flex items-center gap-1" role="group" aria-label="Rating">
      {stars.map((star) => (
        <button
          key={star}
          type="button"
          disabled={readonly}
          onClick={() => onChange?.(star)}
          onMouseEnter={() => !readonly && setHover(star)}
          onMouseLeave={() => !readonly && setHover(0)}
          className={`${sizeClass} transition-all duration-200 ${
            readonly ? "cursor-default" : "cursor-pointer hover:scale-125"
          } ${
            star <= (hover || value)
              ? "text-gold drop-shadow-[0_0_8px_rgba(245,158,11,0.5)]"
              : "text-dark-400"
          }`}
          aria-label={`Rate ${star} stars`}
        >
          ★
        </button>
      ))}
      {value > 0 && (
        <span className="ml-2 text-sm text-dark-300 font-medium">{value}/5</span>
      )}
    </div>
  );
}

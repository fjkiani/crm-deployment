<template>
  <svg
    width="300"
    height="300"
    viewBox="0 0 300 300"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- Rounded brand tile -->
    <path
      d="M214.286 0H85.7143C38.3756 0 0 38.3756 0 85.7143V214.286C0 261.624 38.3756 300 85.7143 300H214.286C261.624 300 300 261.624 300 214.286V85.7143C300 38.3756 261.624 0 214.286 0Z"
      fill="#0F766E"
    />
    <!-- DNA double helix -->
    <g stroke="white" stroke-width="10" stroke-linecap="round" fill="none">
      <!-- Left strand -->
      <path
        d="M105 48
           C 105 72, 195 88, 195 112
           C 195 136, 105 152, 105 176
           C 105 200, 195 216, 195 240
           C 195 256, 150 268, 128 278"
      />
      <!-- Right strand -->
      <path
        d="M195 48
           C 195 72, 105 88, 105 112
           C 105 136, 195 152, 195 176
           C 195 200, 105 216, 105 240
           C 105 256, 150 268, 172 278"
      />
    </g>
    <!-- Base-pair rungs -->
    <g stroke="white" stroke-width="7" stroke-linecap="round" opacity="0.95">
      <line x1="118" y1="72" x2="182" y2="72" />
      <line x1="112" y1="112" x2="188" y2="112" />
      <line x1="118" y1="152" x2="182" y2="152" />
      <line x1="112" y1="192" x2="188" y2="192" />
      <line x1="118" y1="232" x2="182" y2="232" />
    </g>
    <!-- Nucleotide nodes -->
    <g fill="white">
      <circle cx="118" cy="72" r="7" />
      <circle cx="182" cy="72" r="7" />
      <circle cx="112" cy="112" r="7" />
      <circle cx="188" cy="112" r="7" />
      <circle cx="118" cy="152" r="7" />
      <circle cx="182" cy="152" r="7" />
      <circle cx="112" cy="192" r="7" />
      <circle cx="188" cy="192" r="7" />
      <circle cx="118" cy="232" r="7" />
      <circle cx="182" cy="232" r="7" />
    </g>
  </svg>
</template>

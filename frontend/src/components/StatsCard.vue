<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  label: String,
  value: {
    type: Number,
    default: 0,
  },
  icon: {
    type: String,
    default: '📊',
  },
  glow: {
    type: String,
    default: '#8b5cf6',
  },
  subtext: {
    type: String,
    default: '',
  },
})

const displayValue = ref(0)
const duration = 400

const animateTo = (target) => {
  const start = displayValue.value
  const startTime = performance.now()

  const step = (now) => {
    const progress = Math.min((now - startTime) / duration, 1)
    displayValue.value = Math.floor(start + (target - start) * progress)
    if (progress < 1) {
      requestAnimationFrame(step)
    }
  }

  requestAnimationFrame(step)
}

watch(
  () => props.value,
  (val) => animateTo(val ?? 0),
  { immediate: true },
)

const formatted = () => displayValue.value.toLocaleString()
</script>

<template>
  <div class="card" :style="{ boxShadow: `0 12px 30px ${glow}33` }">
    <div class="icon" :style="{ background: `${glow}22`, color: glow }">{{ icon }}</div>
    <p class="label">{{ label }}</p>
    <p class="value">{{ formatted() }}</p>
    <p class="subtext">{{ subtext }}</p>
  </div>
</template>

<style scoped>
.card {
  padding: 1.2rem;
  border-radius: 18px;
  background: rgba(22, 16, 31, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.04);
  min-width: 0;
}
.icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
}
.label {
  margin: 0;
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.25em;
  color: #a893c2;
}
.value {
  margin: 0.2rem 0 0;
  font-size: clamp(1.8rem, 4vw, 2.8rem);
  font-weight: 700;
  color: #fff;
}
.subtext {
  margin: 0.35rem 0 0;
  color: #8f8ba4;
  font-size: 0.85rem;
}
</style>


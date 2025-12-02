<script setup>
const props = defineProps({
  channel: {
    type: String,
    required: true,
  },
  duration: {
    type: Number,
    required: true,
  },
  durations: {
    type: Array,
    default: () => [30, 60, 120, 300],
  },
  isActive: {
    type: Boolean,
    default: false,
  },
  statusText: {
    type: String,
    default: 'Idle',
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:channel', 'update:duration', 'start', 'stop'])

const onSubmit = (event) => {
  event.preventDefault()
  if (props.isActive) {
    emit('stop')
  } else {
    emit('start')
  }
}
</script>

<template>
  <form class="panel" @submit="onSubmit">
    <div class="panel__left">
      <label class="field">
        <span>Channel</span>
        <input
          :value="channel"
          placeholder="e.g. shroud"
          required
          @input="emit('update:channel', $event.target.value)"
        />
      </label>
      <label class="field">
        <span>Duration</span>
        <select :value="duration" @change="emit('update:duration', Number($event.target.value))">
          <option v-for="item in durations" :key="item" :value="item">
            {{ item }}s
          </option>
        </select>
      </label>
    </div>
    <div class="panel__right">
      <p class="status">
        <span :class="['status-dot', isActive ? 'on' : 'off']" />
        {{ statusText }}
      </p>
      <button class="primary" type="submit" :disabled="loading">
        <span v-if="loading">Preparing...</span>
        <span v-else>{{ isActive ? 'Stop' : 'Start' }} Analysis</span>
      </button>
    </div>
  </form>
</template>

<style scoped>
.panel {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 18px;
  background: rgba(20, 16, 40, 0.75);
  border: 1px solid rgba(145, 71, 255, 0.25);
  box-shadow: 0 15px 40px rgba(12, 5, 24, 0.6);
  backdrop-filter: blur(18px);
}

.panel__left {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  flex: 1 1 auto;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  color: #b7b4c7;
  font-size: 0.85rem;
  min-width: 150px;
}

.field input,
.field select {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid transparent;
  border-radius: 12px;
  padding: 0.8rem 1rem;
  color: #fdfbff;
  font-size: 1rem;
  transition: border 0.2s ease, background 0.2s ease;
}

.field input:focus,
.field select:focus {
  outline: none;
  border-color: rgba(145, 71, 255, 0.8);
  background: rgba(255, 255, 255, 0.08);
}

.panel__right {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.6rem;
}

.status {
  margin: 0;
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.2em;
  color: #a393d8;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: block;
  background: rgba(255, 255, 255, 0.25);
}
.status-dot.on {
  background: #4ade80;
  box-shadow: 0 0 8px rgba(74, 222, 128, 0.8);
}
.status-dot.off {
  background: #f87171;
  box-shadow: 0 0 8px rgba(248, 113, 113, 0.8);
}

button.primary {
  padding: 0.85rem 2rem;
  border-radius: 999px;
  border: none;
  font-weight: 600;
  letter-spacing: 0.05em;
  cursor: pointer;
  background: linear-gradient(120deg, #8b5cf6, #c084fc);
  color: #fff;
  text-transform: uppercase;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 12px 25px rgba(139, 92, 246, 0.35);
}
button.primary:disabled {
  opacity: 0.7;
  cursor: wait;
}
button.primary:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 30px rgba(139, 92, 246, 0.45);
}

@media (max-width: 640px) {
  .panel {
    flex-direction: column;
  }
  .panel__left {
    flex-direction: column;
  }
  button.primary {
    width: 100%;
  }
}
</style>


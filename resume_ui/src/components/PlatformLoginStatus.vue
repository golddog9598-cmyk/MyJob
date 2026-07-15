<template>
  <div class="platform-login-status" role="group" aria-label="招聘平台登录状态">
    <button
      v-for="item in platforms"
      :key="item.id"
      type="button"
      :class="{
        selected: activePlatform === item.id,
        'logged-in': platformState(item.id).logged_in,
      }"
      :aria-pressed="activePlatform === item.id"
      :aria-label="`${item.label}，${platformState(item.id).logged_in ? '已登录' : '未登录'}`"
      :title="`${item.label}：${platformState(item.id).logged_in ? '已登录' : '未登录'}，点击切换平台`"
      @click="$emit('select', item.id)"
    >
      <strong>{{ item.label }}</strong>
      <span class="platform-login-state">
        <i aria-hidden="true"></i>
        {{ platformState(item.id).logged_in ? '已登录' : '未登录' }}
      </span>
    </button>
  </div>
</template>

<script setup>
const props = defineProps({
  platforms: { type: Array, default: () => [] },
  platformStatus: { type: Object, default: () => ({}) },
  activePlatform: { type: String, default: 'boss' },
})

defineEmits(['select'])

function platformState(platform) {
  return props.platformStatus?.[platform] || { page_open: false, logged_in: false }
}
</script>

<style scoped>
.platform-login-status {
  width: min(100%, 570px);
  display: grid;
  grid-template-columns: repeat(4, minmax(96px, 1fr));
  gap: 8px;
}

.platform-login-status button {
  min-width: 0;
  height: 46px;
  padding: 5px 10px 6px;
  border: 1px solid var(--app-line-soft);
  border-radius: 11px;
  background: color-mix(in srgb, var(--app-surface-2) 72%, transparent);
  color: var(--app-muted);
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 4px;
  cursor: pointer;
  opacity: .7;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.025);
  transition: transform .18s ease, border-color .18s ease, background .18s ease, color .18s ease, box-shadow .18s ease, opacity .18s ease;
}

.platform-login-status button:hover {
  opacity: 1;
  border-color: var(--app-line);
  transform: translateY(-1px);
}

.platform-login-status button.selected {
  opacity: .92;
  border-color: color-mix(in srgb, var(--app-accent) 48%, var(--app-line));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--app-accent) 16%, transparent);
}

.platform-login-status button.logged-in {
  opacity: 1;
  border-color: color-mix(in srgb, var(--app-success) 58%, var(--app-line));
  background: var(--app-surface);
  color: var(--app-text);
  transform: translateY(-2px);
  box-shadow: 0 9px 20px color-mix(in srgb, var(--app-success) 10%, transparent), inset 0 1px 0 rgba(255,255,255,.05);
}

.platform-login-status button.logged-in:hover {
  transform: translateY(-3px);
}

.platform-login-status button.logged-in.selected {
  border-color: var(--app-success);
  box-shadow: 0 10px 22px color-mix(in srgb, var(--app-success) 14%, transparent), inset 0 0 0 1px color-mix(in srgb, var(--app-success) 20%, transparent);
}

.platform-login-status strong {
  overflow: hidden;
  max-width: 100%;
  font-size: 10px;
  font-weight: 750;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.platform-login-state {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  font-size: 8px;
  font-weight: 650;
  line-height: 1;
}

.platform-login-state i {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: color-mix(in srgb, var(--app-muted) 64%, transparent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--app-muted) 10%, transparent);
}

.logged-in .platform-login-state {
  color: var(--app-success);
}

.logged-in .platform-login-state i {
  background: var(--app-success);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--app-success) 16%, transparent);
}

@media (prefers-reduced-motion: reduce) {
  .platform-login-status button,
  .platform-login-status button:hover,
  .platform-login-status button.logged-in,
  .platform-login-status button.logged-in:hover {
    transition: none;
    transform: none;
  }
}

@media (max-width: 1280px) and (min-width: 981px) {
  .platform-login-status {
    grid-template-columns: repeat(4, minmax(72px, 1fr));
    gap: 6px;
  }

  .platform-login-status button {
    padding-inline: 6px;
  }
}
</style>

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import test from 'node:test'

const source = readFileSync(new URL('../../browser_extension/platformContent.js', import.meta.url), 'utf8')

function textElement(text) {
  return {
    getAttribute(name) {
      return name === 'title' ? '' : null
    },
    innerText: text,
  }
}

test('BOSS extraction starts from detail links and falls back to link text for the title', () => {
  const fields = new Map([
    ['.salary', textElement('\uE032\uE036-\uE033\uE031K')],
    ['.company-name', textElement('易伙人科技')],
    ['.job-area', textElement('南宁·良庆区·青山路')],
  ])
  const card = {
    innerText: 'AI Agent 业务落地专家\n20-30K\n易伙人科技\n南宁·良庆区·青山路\n3-5年\n本科',
    querySelector(selector) {
      return fields.get(selector) || null
    },
  }
  const negotiableFields = new Map([
    ['.salary', textElement('面议')],
    ['.company-name', textElement('测试公司')],
    ['.job-area', textElement('南宁')],
  ])
  const negotiableCard = {
    innerText: '测试岗位\n面议\n测试公司\n南宁',
    querySelector(selector) {
      return negotiableFields.get(selector) || null
    },
  }
  const anchor = {
    href: 'https://www.zhipin.com/job_detail/test.html',
    innerText: 'AI Agent 业务落地专家',
    getAttribute(name) {
      if (name === 'href') return '/job_detail/test.html'
      if (name === 'title') return ''
      return null
    },
    closest() {
      return card
    },
  }
  const navigationAnchor = {
    href: 'https://www.zhipin.com/job_detail/',
    innerText: '职位搜索',
    getAttribute(name) {
      if (name === 'href') return '/job_detail/'
      return null
    },
    closest() {
      return { innerText: '职位搜索', querySelector() { return null } }
    },
  }
  const negotiableAnchor = {
    href: 'https://www.zhipin.com/job_detail/negotiable.html',
    innerText: '测试岗位',
    getAttribute(name) {
      if (name === 'href') return '/job_detail/negotiable.html'
      return null
    },
    closest() {
      return negotiableCard
    },
  }
  const context = {
    chrome: { runtime: { onMessage: { addListener() {} } } },
    document: {
      querySelectorAll(selector) {
        assert.equal(selector, 'a[href*="/job_detail/"]')
        return [navigationAnchor, anchor, negotiableAnchor]
      },
    },
    location: { hostname: 'www.zhipin.com' },
    Set,
  }

  vm.createContext(context)
  vm.runInContext(source, context)
  const jobs = vm.runInContext('extractBoss(60)', context)

  assert.equal(jobs.length, 2)
  assert.equal(jobs[0].job_title, 'AI Agent 业务落地专家')
  assert.equal(jobs[0].company, '易伙人科技')
  assert.equal(jobs[0].city, '南宁·良庆区·青山路')
  assert.equal(jobs[0].job_url, 'https://www.zhipin.com/job_detail/test.html')
  assert.equal(jobs[0].salary, '15-20K')
  assert.equal(jobs[1].salary, '面议')
})

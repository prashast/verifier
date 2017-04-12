#!/usr/bin/python
import re
import sys
def main(filename, markdown_file=None):
	fo = open(filename, "r") #the objdump file to be parsed
	remove = []
	rem_list = []
	objdump_list = []
	list2 = []
	final_objdump=[]
	instructions = []
	guard=[]
	flag = flag1 = count = count1 = count2 = count3 = start = end = flag_rep = 0
	s = ''
	buf=''
	regexObject = re.compile(r"^\s[\w]+:\t[\w]+[\s][\w]{0,4}")
	regexObject1 = re.compile(r"; [\w]+")

	for index,lines in enumerate(fo.readlines()):
		result = regexObject.sub("",lines)
		result1 = regexObject1.sub("",result)
		result1=result1.strip()
        	objdump_list.append(result1)
		if flag_rep == 1 and re.match(r'msr\tCPSR_f, r0',result1):
			flag_rep+=1
			flag=9
			continue
			#print "flag_rep=0",result1
		elif flag_rep == 1:
			continue

		if flag == 0:
			if re.match(r'push\t{r0}',result1):
				flag = 1
				start = index #store start index of escalated region

		elif flag == 1:
			if re.match(r'mrs\tr0, CPSR',result1):
				flag = 2
			else:
				flag = 0

		elif flag == 2:
			if re.match(r'push\t{r0}',result1):
				flag = 3
			else:
				flag = 0

		elif flag == 3:
			if re.match(r'mrs\tr0, CONTROL',result1):
				flag = 4
			else:
				flag = 0

		elif flag == 4:
			if re.match(r'tst.w\tr0, #1',result1):
				flag = 5
			else:
				flag = 0

		elif flag == 5:
			if re.match(r'it\tne',result1):
				flag = 6
			else:
				flag = 0

		elif flag == 6:
			if re.match(r'svcne\t254',result1):
				flag = 7
			else:
				flag = 0

		elif flag == 7:
			if re.match(r'pop\t{r0}',result1):
				flag = 8
			else:
				flag = 0

		elif flag == 8:
			if re.match(r'msr\tCPSR_f, r0',result1):
				flag = 9
			else:
				flag = 0

		elif flag == 9:
			if re.match(r'pop\t{r0}',result1):
				flag = 10
			else:
				flag = 0

		elif flag == 10:
			if re.match(r'push\t{r0}',result1):
				flag = 11
				buf = buf+result1+'\n'
				continue
			guard.append(index)
			s=s+result1+'\n'

		elif flag == 11:
			if re.match(r'mrs\tr0, CONTROL',result1):
				flag = 12
				buf = buf+result1+'\n'

			elif re.match(r'mrs\tr0, CPSR', result1):
				flag_rep+=1
				continue
			else:
				print 'FLAG--10'
				s = s+result1+'\n'
				flag = 10
		elif flag == 12:
			if re.match(r'orr.w\tr0, r0, #1',result1):
				flag = 13
				buf = buf + result1 + '\n'
			else:
				s =s + buf + result1+'\n'
				flag = 10
		elif flag == 13:
			if re.match(r'msr\tCONTROL, r0',result1):
				buf = buf + result1 + '\n'
				flag = 14
			else:
				s=s+result1+'\n'
				flag = 10
		elif flag == 14:
			if re.match(r'pop\t{r0}',result1):
				if flag_rep == 2:
					flag=10
					flag_rep=0
					continue
				flag = flag_rep = 0
				count+=1
				end=index #store end index of escalated region
				list2.append(s)
				instructions.append(guard)
				guard=[]
				for x in range(start,end+1):
					remove.append(x)
				start = end = 0
				s=''
				buf=''
			else:
				flag=10
				s=s + buf + result1+'\n'

	'''Removing all the protected instructions including the guards'''
	for index,item in enumerate(objdump_list):
		if index not in remove:
			final_objdump.append(item)
	fo.seek(0)

	for i in instructions:
		for index,item in enumerate(fo.readlines()):
			if index in i:
				print item
		fo.seek(0)
		print '<----------------->'


	regexObject_mov = re.compile(r'^(mov[.]*[a-z]*)\t(r\d)') #searches for mo(v/w/s/.w) instr
	regexObject_str = re.compile(r'\[(r\d)') #searches for registers in ldr,str
	protected = {'movt':[],'movw':[],'mov':[]}
	yes = partial = length = max_length = 0

	for item in list2:
		ab = ''.join(item)
		ab=ab.split('\n')
		ab = filter(None,ab)
		#print item
		if(len(ab) > max_length):
			max_length = len(ab)
		length += len(ab)
		for items in ab:
			match = regexObject_mov.match(items)
			match1 = regexObject_str.search(items)
			if match:
				if(match.group(1) == 'movw' or match.group(1) == 'mov.w' or match.group(1) == 'movs'):
					protected['movw'].append(match.group(2))
				elif(match.group(1) == 'movt'):
					protected['movt'].append(match.group(2))
				elif (match.group(1) == 'mov'):
					protected['mov'].append(match.group(2))
			elif match1:
				#print match1.group(0)
				if ((match1.group(1) in protected['movw'] and match1.group(1) in protected['movt']) or match1.group(1) in protected['mov']):
					yes+=1
				else:
					partial+=1
		protected = {'movt':[],'movw':[],'mov':[]}


	for item in final_objdump:
		if re.match(r'msr',item) or re.match(r'cps',item):
			count1+=1
		if re.match(r'mrs',item):
			count2+=1
		if re.match(r'cps',item):
			count3+=1

	try:
		ave_prot_instr_count = length/float(count)
	except ZeroDivisionError:
		ave_prot_instr_count=0


	print "Number of mrs instructions found in binary:",count2
	print "Number of cps instructions found in binary:",count3
	print "Number of unprotected instructions:",(count1-2)
	print "Number of guarded regions:",count
	print "Average instruction count in the protected region", ave_prot_instr_count
	print "Maximum number of instructions in a protected region",(max_length)
	print "No Data Leak Loads/Stores:",yes
	print "Partial Data Leak Loads/Stores:",partial
	if markdown_file:
		with open(markdown_file,'at') as md_file:
			md_file.write('| %s | %i | %i | %i | %i | %0.2f | %i | %i | %i |\n'%\
			 (filename, count2 , count3, count1-2, count,ave_prot_instr_count,
			  max_length, yes, partial))

if __name__=='__main__':
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('-f','--file',dest='file',required=True,
                        help= "File to parse")

	parser.add_argument('--markdown',dest='md',default=None,
                        help= "File to parse")

	args= parser.parse_args()
	main(args.file,args.md)
